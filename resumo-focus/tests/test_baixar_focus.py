from datetime import date
from unittest.mock import Mock, patch

import pytest

from src.baixar_focus import (
    baixar_conteudo,
    baixar_focus_mais_recente,
    encontrar_pdf_mais_recente,
    montar_url,
    salvar_pdf,
    ultima_segunda_feira,
)

pytestmark = pytest.mark.offline


def test_montar_url():
    assert montar_url(date(2024, 1, 5)) == (
        "https://www.bcb.gov.br/content/focus/focus/R20240105.pdf"
    )


@pytest.mark.parametrize(
    "referencia, esperado",
    [
        (date(2024, 1, 8), date(2024, 1, 8)),  # já é segunda
        (date(2024, 1, 10), date(2024, 1, 8)),  # quarta -> segunda anterior
        (date(2024, 1, 14), date(2024, 1, 8)),  # domingo -> segunda anterior
    ],
)
def test_ultima_segunda_feira(referencia, esperado):
    assert ultima_segunda_feira(referencia) == esperado


def _resposta(status_code, conteudo=b""):
    resposta = Mock()
    resposta.status_code = status_code
    resposta.content = conteudo
    if status_code >= 400 and status_code != 404:
        resposta.raise_for_status.side_effect = Exception("erro http")
    else:
        resposta.raise_for_status.return_value = None
    return resposta


@patch("src.baixar_focus.requests.get")
def test_baixar_conteudo_retorna_bytes_quando_200(mock_get):
    mock_get.return_value = _resposta(200, b"conteudo-pdf")
    assert baixar_conteudo("http://exemplo.com") == b"conteudo-pdf"


@patch("src.baixar_focus.requests.get")
def test_baixar_conteudo_retorna_none_quando_404(mock_get):
    mock_get.return_value = _resposta(404)
    assert baixar_conteudo("http://exemplo.com") is None


@patch("src.baixar_focus.baixar_conteudo")
def test_encontrar_pdf_mais_recente_recua_em_feriado(mock_baixar):
    # segunda (404, feriado) -> domingo (404) -> sábado (200)
    mock_baixar.side_effect = [None, None, b"conteudo-pdf"]

    conteudo, data_encontrada = encontrar_pdf_mais_recente(date(2024, 1, 8))

    assert conteudo == b"conteudo-pdf"
    assert data_encontrada == date(2024, 1, 6)
    assert mock_baixar.call_count == 3


@patch("src.baixar_focus.baixar_conteudo")
def test_encontrar_pdf_mais_recente_desiste_apos_limite(mock_baixar):
    mock_baixar.return_value = None

    with pytest.raises(RuntimeError):
        encontrar_pdf_mais_recente(date(2024, 1, 8), max_tentativas=3)

    assert mock_baixar.call_count == 3


def test_salvar_pdf_grava_no_caminho_esperado(tmp_path):
    caminho = salvar_pdf(b"conteudo-pdf", date(2024, 1, 8), pasta_destino=tmp_path)

    assert caminho == tmp_path / "focus_2024-01-08.pdf"
    assert caminho.read_bytes() == b"conteudo-pdf"


@patch("src.baixar_focus.encontrar_pdf_mais_recente")
def test_baixar_focus_mais_recente_usa_ultima_segunda_como_ponto_de_partida(
    mock_encontrar, tmp_path
):
    mock_encontrar.return_value = (b"conteudo-pdf", date(2024, 1, 8))

    caminho = baixar_focus_mais_recente(
        referencia=date(2024, 1, 10), pasta_destino=tmp_path
    )

    data_inicial_usada = mock_encontrar.call_args[0][0]
    assert data_inicial_usada == date(2024, 1, 8)
    assert caminho == tmp_path / "focus_2024-01-08.pdf"


@pytest.mark.online
def test_baixar_focus_mais_recente_baixa_pdf_real(tmp_path):
    """Teste de integração: acessa de fato o site do BCB.

    Não roda por padrão (veja pytest.ini). Para rodar: pytest -m online
    """
    caminho = baixar_focus_mais_recente(pasta_destino=tmp_path)

    assert caminho.exists()
    assert caminho.read_bytes()[:4] == b"%PDF"


@pytest.mark.online
def test_montar_url_aponta_para_pdf_existente():
    """Teste de integração: confirma que a URL de uma data conhecida resolve
    de fato para um PDF real (valida o padrão de URL contra o site real)."""
    conteudo = baixar_conteudo(montar_url(date(2024, 1, 5)))

    assert conteudo is not None
    assert conteudo[:4] == b"%PDF"

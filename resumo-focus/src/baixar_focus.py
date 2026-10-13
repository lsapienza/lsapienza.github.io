"""Baixa o PDF mais recente do Boletim Focus do Banco Central do Brasil.

Este módulo é puramente mecânico: localiza e baixa o arquivo. Não interpreta
nem extrai conteúdo do PDF (ver CLAUDE.md — princípio de separação entre
determinístico e julgamento).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = "https://www.bcb.gov.br/content/focus/focus/R{data}.pdf"
# O PDF leva a data da sexta de referência (ex.: R20261009 para o relatório
# de 9/10, publicado na segunda seguinte). Recuar até 3 dias (sex, qui, qua)
# cobre um feriado na sexta sem nunca cair no relatório da semana anterior.
MAX_TENTATIVAS = 3
TIMEOUT_SEGUNDOS = 30
PASTA_DESTINO_PADRAO = Path("data")

logger = logging.getLogger(__name__)


class FocusAindaNaoPublicado(RuntimeError):
    """O relatório da semana ainda não está no site do BCB (feriado/atraso)."""


def montar_url(data_alvo: date) -> str:
    """Monta a URL do PDF do Focus para uma data específica."""
    return BASE_URL.format(data=data_alvo.strftime("%Y%m%d"))


def ultima_segunda_feira(referencia: date) -> date:
    """Retorna a data da última segunda-feira até e incluindo `referencia`."""
    return referencia - timedelta(days=referencia.weekday())


def sexta_de_referencia(referencia: date) -> date:
    """Sexta-feira cujo relatório é publicado na semana de `referencia`."""
    return ultima_segunda_feira(referencia) - timedelta(days=3)


def baixar_conteudo(url: str, timeout: int = TIMEOUT_SEGUNDOS) -> bytes | None:
    """Baixa o conteúdo de uma URL.

    Retorna os bytes do PDF quando o recurso existe (HTTP 200), ou None
    quando não existe (HTTP 404 — ex.: feriado adiou a publicação). Outros
    erros de HTTP são propagados como exceção.
    """
    resposta = requests.get(url, timeout=timeout)
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.content


def encontrar_pdf_mais_recente(
    data_inicial: date, max_tentativas: int = MAX_TENTATIVAS
) -> tuple[bytes, date]:
    """Procura o PDF do Focus a partir de `data_inicial`.

    Recua um dia por tentativa em caso de 404, até `max_tentativas` vezes.
    """
    data_alvo = data_inicial
    for tentativa in range(1, max_tentativas + 1):
        url = montar_url(data_alvo)
        logger.info("Tentativa %d/%d: %s", tentativa, max_tentativas, url)
        conteudo = baixar_conteudo(url)
        if conteudo is not None:
            return conteudo, data_alvo
        data_alvo -= timedelta(days=1)

    raise FocusAindaNaoPublicado(
        f"Nenhum PDF do Focus encontrado em {max_tentativas} tentativas "
        f"a partir de {data_inicial.isoformat()}."
    )


def salvar_pdf(
    conteudo: bytes, data_alvo: date, pasta_destino: Path = PASTA_DESTINO_PADRAO
) -> Path:
    """Salva o conteúdo do PDF em `pasta_destino/focus_AAAA-MM-DD.pdf`."""
    pasta_destino.mkdir(parents=True, exist_ok=True)
    caminho = pasta_destino / f"focus_{data_alvo.isoformat()}.pdf"
    caminho.write_bytes(conteudo)
    return caminho


def baixar_focus_mais_recente(
    referencia: date | None = None,
    pasta_destino: Path = PASTA_DESTINO_PADRAO,
    max_tentativas: int = MAX_TENTATIVAS,
) -> Path:
    """Ponto de entrada: localiza, baixa e salva o Boletim Focus da semana.

    Se o PDF da semana já estiver em `pasta_destino`, não baixa de novo.
    Levanta FocusAindaNaoPublicado se o relatório da semana ainda não saiu —
    nunca recua até o relatório da semana anterior.
    """
    referencia = referencia or date.today()
    data_inicial = sexta_de_referencia(referencia)
    for i in range(max_tentativas):
        existente = pasta_destino / f"focus_{(data_inicial - timedelta(days=i)).isoformat()}.pdf"
        if existente.exists():
            logger.info("PDF da semana já baixado: %s", existente)
            return existente
    conteudo, data_encontrada = encontrar_pdf_mais_recente(data_inicial, max_tentativas)
    return salvar_pdf(conteudo, data_encontrada, pasta_destino)


def main() -> None:
    # Logs vão para stderr; o stdout fica só com o caminho do PDF (ou vazio se
    # o relatório da semana ainda não saiu), para o workflow consumir.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        caminho = baixar_focus_mais_recente()
    except FocusAindaNaoPublicado as erro:
        logger.warning("Focus da semana ainda não publicado: %s", erro)
        return
    logger.info("PDF em %s", caminho)
    print(caminho)


if __name__ == "__main__":
    main()

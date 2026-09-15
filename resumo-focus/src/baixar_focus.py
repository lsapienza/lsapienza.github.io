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
MAX_TENTATIVAS = 10
TIMEOUT_SEGUNDOS = 30
PASTA_DESTINO_PADRAO = Path("data")

logger = logging.getLogger(__name__)


def montar_url(data_alvo: date) -> str:
    """Monta a URL do PDF do Focus para uma data específica."""
    return BASE_URL.format(data=data_alvo.strftime("%Y%m%d"))


def ultima_segunda_feira(referencia: date) -> date:
    """Retorna a data da última segunda-feira até e incluindo `referencia`."""
    return referencia - timedelta(days=referencia.weekday())


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

    raise RuntimeError(
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
    """Ponto de entrada: localiza, baixa e salva o Boletim Focus mais recente."""
    referencia = referencia or date.today()
    data_inicial = ultima_segunda_feira(referencia)
    conteudo, data_encontrada = encontrar_pdf_mais_recente(data_inicial, max_tentativas)
    return salvar_pdf(conteudo, data_encontrada, pasta_destino)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    caminho = baixar_focus_mais_recente()
    logger.info("PDF salvo em %s", caminho)


if __name__ == "__main__":
    main()

"""Extrai texto puro do PDF do Boletim Focus.

Este módulo é puramente mecânico: converte o PDF em texto bruto. Não
interpreta, filtra, resume ou reformata o conteúdo (ver CLAUDE.md —
princípio de separação entre determinístico e julgamento).
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def ler_texto_do_pdf(caminho_pdf: Path) -> str:
    """Lê todas as páginas de um PDF e retorna o texto concatenado."""
    textos_por_pagina = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            textos_por_pagina.append(pagina.extract_text() or "")
    return "\n\n".join(textos_por_pagina)


def caminho_txt_correspondente(caminho_pdf: Path) -> Path:
    """Deriva o caminho do .txt a partir do caminho do .pdf (mesma pasta/nome)."""
    return caminho_pdf.with_suffix(".txt")


def salvar_texto(texto: str, caminho_txt: Path) -> Path:
    """Salva o texto extraído em disco (UTF-8)."""
    caminho_txt.parent.mkdir(parents=True, exist_ok=True)
    caminho_txt.write_text(texto, encoding="utf-8")
    return caminho_txt


def extrair_e_salvar(caminho_pdf: Path) -> Path:
    """Ponto de entrada: extrai o texto do PDF e salva como .txt ao lado dele."""
    texto = ler_texto_do_pdf(caminho_pdf)
    caminho_txt = caminho_txt_correspondente(caminho_pdf)
    return salvar_texto(texto, caminho_txt)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Extrai texto de um PDF do Boletim Focus.")
    parser.add_argument("caminho_pdf", type=Path, help="Caminho do PDF a processar")
    args = parser.parse_args()

    caminho_txt = extrair_e_salvar(args.caminho_pdf)
    logger.info("Texto salvo em %s", caminho_txt)


if __name__ == "__main__":
    main()

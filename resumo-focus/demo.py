"""Demo do pipeline local: baixa e extrai o Boletim Focus mais recente.

Uso:
    python demo.py              # baixa, extrai e mostra o caminho do .txt
    python demo.py --abrir      # além disso, abre o .txt no visualizador padrão
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from src.baixar_focus import baixar_focus_mais_recente
from src.extrair_texto import extrair_e_salvar

logger = logging.getLogger(__name__)


def abrir_arquivo(caminho: Path) -> None:
    """Abre um arquivo com o aplicativo padrão do sistema operacional."""
    if sys.platform == "win32":
        os.startfile(caminho)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(caminho)], check=True)
    else:
        subprocess.run(["xdg-open", str(caminho)], check=True)


def executar_pipeline(abrir: bool = False) -> Path:
    """Baixa o Focus mais recente e extrai o texto. Retorna o caminho do .txt."""
    logger.info("Baixando o Boletim Focus mais recente...")
    caminho_pdf = baixar_focus_mais_recente()
    logger.info("PDF salvo em %s", caminho_pdf)

    logger.info("Extraindo texto do PDF...")
    caminho_txt = extrair_e_salvar(caminho_pdf)
    logger.info("Texto salvo em %s", caminho_txt)

    if abrir:
        abrir_arquivo(caminho_txt)

    return caminho_txt


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Baixa e extrai o Boletim Focus mais recente (pipeline local)."
    )
    parser.add_argument(
        "--abrir", action="store_true", help="Abre o .txt resultante ao final"
    )
    args = parser.parse_args()
    executar_pipeline(abrir=args.abrir)


if __name__ == "__main__":
    main()

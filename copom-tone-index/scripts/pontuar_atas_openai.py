"""Ponta a ponta: coleta as atas, recorta as seções A/B e pontua com OpenAI.

Uso:
    python scripts/pontuar_atas_openai.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coleta.atas_copom import coletar_atas, extrair_secoes_a_b  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from pontuacao.loop_openai import pontuar_atas_openai  # noqa: E402


def main() -> None:
    atas = coletar_atas()
    atas_recortadas = [
        Document(page_content=extrair_secoes_a_b(ata.page_content), metadata=ata.metadata)
        for ata in atas
    ]
    pontuar_atas_openai(atas_recortadas)


if __name__ == "__main__":
    main()

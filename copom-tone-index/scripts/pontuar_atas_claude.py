"""Ponta a ponta: coleta as atas, recorta as seções A/B e pontua com Claude.

Uso:
    python scripts/pontuar_atas_claude.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

CAMINHO_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAMINHO_PROJETO / "src"))

# Carrega ANTHROPIC_API_KEY do .env explicitamente — não depende do
# terminal ou do editor injetar as variáveis de ambiente sozinho.
load_dotenv(CAMINHO_PROJETO / ".env")

from coleta.atas_copom import coletar_atas, extrair_secoes_a_b  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from pontuacao.loop_claude import pontuar_atas_claude  # noqa: E402


def main() -> None:
    atas = coletar_atas()
    atas_recortadas = [
        Document(page_content=extrair_secoes_a_b(ata.page_content), metadata=ata.metadata)
        for ata in atas
    ]
    pontuar_atas_claude(atas_recortadas)


if __name__ == "__main__":
    main()

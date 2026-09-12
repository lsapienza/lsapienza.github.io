"""Junta os três caches de score (Gemini, Claude, OpenAI) com a variação
da Selic numa única tabela, e grava em data/tabela_final.csv.

Pressupõe que os três scripts de pontuação (pontuar_atas_*.py) já foram
rodados pelo menos uma vez, gerando os respectivos scores_*_cache.csv.

Uso:
    python scripts/montar_tabela_final.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pontuacao.tabela_final import montar_tabela_final  # noqa: E402

CAMINHO_SAIDA = Path(__file__).resolve().parent.parent / "data" / "tabela_final.csv"


def main() -> None:
    tabela = montar_tabela_final()
    CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(CAMINHO_SAIDA, index=False)
    print(f"Tabela final com {len(tabela)} reuniões salva em {CAMINHO_SAIDA}")
    print(tabela)


if __name__ == "__main__":
    main()

"""Calibra uma regressão OLS por modelo (3 LLMs + baseline léxico) contra a
variação da Selic, e testa (via Vuong) quando a diferença entre dois
modelos é estatisticamente robusta.

Lê data/tabela_final.csv, gerada por scripts/montar_tabela_final.py.

Uso:
    python scripts/calibrar_modelos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402
from avaliacao.calibracao import (  # noqa: E402
    montar_tabela_calibracao,
    montar_tabela_comparacoes,
)

CAMINHO_TABELA_FINAL = Path(__file__).resolve().parent.parent / "data" / "tabela_final.csv"
CAMINHO_SAIDA_CALIBRACAO = (
    Path(__file__).resolve().parent.parent / "data" / "tabela_calibracao.csv"
)
CAMINHO_SAIDA_COMPARACOES = (
    Path(__file__).resolve().parent.parent / "data" / "tabela_comparacoes_vuong.csv"
)


def main() -> None:
    tabela_final = pd.read_csv(CAMINHO_TABELA_FINAL)

    tabela_calibracao = montar_tabela_calibracao(tabela_final)
    tabela_calibracao.to_csv(CAMINHO_SAIDA_CALIBRACAO, index=False)
    print("=== Calibração OLS por modelo (variacao_selic ~ score) ===")
    print(tabela_calibracao.to_string(index=False))

    tabela_comparacoes = montar_tabela_comparacoes(tabela_final)
    tabela_comparacoes.to_csv(CAMINHO_SAIDA_COMPARACOES, index=False)
    print("\n=== Comparações par a par (teste de Vuong, 1989) ===")
    print(tabela_comparacoes.to_string(index=False))


if __name__ == "__main__":
    main()

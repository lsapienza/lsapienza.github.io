"""Gera os três gráficos do Índice de Tom (plotnine) e salva em PNG.

Lê data/tabela_final.csv e data/tabela_calibracao.csv (geradas por
scripts/montar_tabela_final.py e scripts/calibrar_modelos.py).

`.save(..., verbose=False)` mantém o salvamento silencioso — é o
equivalente, fora de um notebook/Quarto, de um chunk com `#| echo: false`
e `#| output: false`: quando este mesmo código for embutido no .qmd do
paper, use esses dois chunk options para não poluir o documento renderizado
com texto de progresso, só a figura.

Uso:
    python scripts/gerar_graficos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402
from visualizacao.graficos import (  # noqa: E402
    grafico_comparativo_selic,
    grafico_indice_tom_calibrado,
    grafico_zscore_tom,
)

DIRETORIO_DADOS = Path(__file__).resolve().parent.parent / "data"
DIRETORIO_FIGURAS = DIRETORIO_DADOS / "figuras"


def main() -> None:
    tabela_final = pd.read_csv(DIRETORIO_DADOS / "tabela_final.csv")
    tabela_calibracao = pd.read_csv(DIRETORIO_DADOS / "tabela_calibracao.csv")

    DIRETORIO_FIGURAS.mkdir(parents=True, exist_ok=True)

    grafico1 = grafico_indice_tom_calibrado(tabela_final, tabela_calibracao)
    grafico1.save(
        DIRETORIO_FIGURAS / "indice_tom_calibrado.png", dpi=200, verbose=False
    )

    grafico2 = grafico_zscore_tom(tabela_final)
    grafico2.save(DIRETORIO_FIGURAS / "zscore_tom.png", dpi=200, verbose=False)

    grafico3 = grafico_comparativo_selic(tabela_final, tabela_calibracao)
    grafico3.save(
        DIRETORIO_FIGURAS / "comparativo_selic.png", dpi=200, verbose=False
    )

    print(f"Gráficos salvos em {DIRETORIO_FIGURAS}")


if __name__ == "__main__":
    main()

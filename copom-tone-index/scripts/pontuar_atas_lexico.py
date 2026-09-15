"""Ponta a ponta: coleta as atas, recorta as seções A/B e pontua com o
léxico hawkish/dovish (baseline, sem cache — cálculo instantâneo).

Uso:
    python scripts/pontuar_atas_lexico.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402
from coleta.atas_copom import coletar_atas, extrair_secoes_a_b  # noqa: E402
from pontuacao.lexico import pontuar_com_lexico  # noqa: E402

CAMINHO_SAIDA = Path(__file__).resolve().parent.parent / "data" / "scores_lexico.csv"


def main() -> None:
    atas = coletar_atas()
    linhas = []
    for indice, ata in enumerate(atas, start=1):
        nro_reuniao = ata.metadata["nro_reuniao"]
        texto_recortado = extrair_secoes_a_b(ata.page_content)
        resultado = pontuar_com_lexico(texto_recortado)
        print(
            f"[{indice}/{len(atas)}] reunião {nro_reuniao}: "
            f"score = {resultado['score']:+.2f} "
            f"(n_hawkish={resultado['n_hawkish']}, n_dovish={resultado['n_dovish']})"
        )
        linhas.append(
            {
                "nro_reuniao": nro_reuniao,
                "data": ata.metadata.get("data"),
                "score": resultado["score"],
                "n_hawkish": resultado["n_hawkish"],
                "n_dovish": resultado["n_dovish"],
            }
        )

    tabela = pd.DataFrame(linhas).sort_values("nro_reuniao")
    CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(CAMINHO_SAIDA, index=False)
    print(f"{len(tabela)} atas pontuadas pelo léxico, salvas em {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()

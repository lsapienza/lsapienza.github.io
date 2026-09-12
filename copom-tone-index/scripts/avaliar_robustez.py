"""Três exercícios de robustez para variacao_selic ~ score, por modelo:

1. In-sample  — a inferência OLS de calibracao.py (β̂, IC 95%, R²).
2. Holdout    — calibra no treino, mede RMSE/MAE nas últimas 6 reuniões.
3. Walk-forward — janela expansiva (treino mínimo 20), RMSE/MAE médios
   sobre ~26 previsões fora da amostra, uma por reunião.

Lê data/tabela_final.csv, gerada por scripts/montar_tabela_final.py.

Uso:
    python scripts/avaliar_robustez.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402
from avaliacao.calibracao import montar_tabela_calibracao  # noqa: E402
from avaliacao.robustez import montar_tabela_holdout, montar_tabela_walk_forward  # noqa: E402

CAMINHO_TABELA_FINAL = Path(__file__).resolve().parent.parent / "data" / "tabela_final.csv"
DIRETORIO_SAIDA = Path(__file__).resolve().parent.parent / "data"

EXPLICACAO_JANELA_CALMA = """\
Por que o walk-forward existe além do holdout — o viés de "janela calma":
um holdout fixo julga cada modelo só nas últimas seis reuniões. Se esse
bloco cair, por acaso, num trecho "calmo" do ciclo de juros (Selic parada
ou mudando pouco), QUALQUER modelo — inclusive um sem sinal nenhum — tende
a errar pouco ali, simplesmente porque o alvo mal se move; o resultado do
holdout passa a refletir mais o regime que calhou de cair no fim da
amostra do que a qualidade real do modelo, ofuscando a vantagem de um
modelo genuinamente melhor. Se o bloco cair num trecho de ciclo agressivo
de aperto ou corte, o viés vai na direção oposta. Em ambos os casos, a
comparação entre modelos fica refém de qual pedaço específico da história
virou o teste — um acidente de quando os dados foram coletados, não uma
propriedade do modelo.

O walk-forward usa cada reunião da amostra (após o treino mínimo de 20)
exatamente uma vez como ponto de teste, treinado só com o que já era
conhecido até ali — uma simulação honesta de uso em tempo real — e agrega
o erro sobre ~26 previsões espalhadas por vários regimes distintos (ciclos
de alta, de baixa, de pausa). Nenhum trecho isolado de calmaria ou de
turbulência domina o resultado sozinho, ao contrário do que pode acontecer
com um holdout de só seis pontos.
"""


def main() -> None:
    tabela_final = pd.read_csv(CAMINHO_TABELA_FINAL)

    print("=== 1) In-sample (OLS, toda a amostra) ===")
    tabela_in_sample = montar_tabela_calibracao(tabela_final)
    tabela_in_sample.to_csv(DIRETORIO_SAIDA / "robustez_in_sample.csv", index=False)
    print(tabela_in_sample.to_string(index=False))

    print("\n=== 2) Holdout (treino = tudo exceto as últimas 6 reuniões) ===")
    tabela_holdout = montar_tabela_holdout(tabela_final, n_teste=6)
    tabela_holdout.to_csv(DIRETORIO_SAIDA / "robustez_holdout.csv", index=False)
    print(tabela_holdout.to_string(index=False))

    print("\n=== 3) Walk-forward (janela expansiva, treino mínimo 20) ===")
    tabela_wf = montar_tabela_walk_forward(tabela_final, treino_minimo=20)
    tabela_wf.to_csv(DIRETORIO_SAIDA / "robustez_walk_forward.csv", index=False)
    print(tabela_wf.to_string(index=False))

    print("\n" + EXPLICACAO_JANELA_CALMA)


if __name__ == "__main__":
    main()

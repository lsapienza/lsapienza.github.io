"""Três exercícios de robustez para a calibração variacao_selic ~ score:

1. In-sample: a própria inferência OLS (β̂, IC 95%, R²) — já implementada
   em `calibracao.py`. Mede ajuste, não capacidade preditiva.
2. Holdout: calibra α̂/β̂ só no treino e mede RMSE/MAE num bloco fixo fora
   da amostra (as últimas seis reuniões).
3. Walk-forward (janela expansiva, treino mínimo de 20 atas): para cada
   reunião a partir da 21ª, treina em tudo que veio antes e prevê só essa
   reunião; repete deslizando a janela por toda a amostra.

Por que o walk-forward existe além do holdout — o viés de "janela calma":
um holdout fixo julga o modelo só nas últimas seis reuniões. Se esse
bloco por acaso cair num trecho "calmo" do ciclo de juros (Selic parada
ou mudando pouco), QUALQUER modelo — inclusive um sem sinal nenhum — tende
a errar pouco ali, porque o alvo mal se move; o resultado do holdout
reflete mais o regime que calhou de cair no fim da amostra do que a
qualidade real do modelo. Se o bloco calhar de cair num trecho de ciclo
agressivo de aperto ou corte, o viés vai na direção oposta. Em ambos os
casos, a comparação entre modelos fica refém de qual pedaço específico da
história virou o teste — um acidente de quando os dados foram coletados,
não uma propriedade do modelo. O walk-forward usa cada reunião da amostra
(após o treino mínimo) exatamente uma vez como ponto de teste, treinada
só com o que já era conhecido até ali — uma simulação honesta de uso em
tempo real — e agrega o erro sobre ~26 previsões espalhadas por vários
regimes distintos (ciclos de alta, de baixa, de pausa). Nenhum trecho
isolado de calmaria ou de turbulência domina o resultado sozinho, ao
contrário do que pode acontecer com um holdout de só seis pontos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .calibracao import ESPECIFICACOES_MODELOS


def _preparar_series_ordenadas(tabela: pd.DataFrame, coluna_score: str) -> tuple[np.ndarray, np.ndarray]:
    """Ordena a tabela por nro_reuniao (ordem cronológica) e devolve os arrays
    score/variacao_selic alinhados por posição — a base de qualquer exercício
    que dependa da ordem temporal (holdout, walk-forward).
    """
    ordenada = tabela.sort_values("nro_reuniao").reset_index(drop=True)
    return ordenada[coluna_score].to_numpy(dtype=float), ordenada["variacao_selic"].to_numpy(dtype=float)


def _ajustar_ols(score_treino: np.ndarray, y_treino: np.ndarray) -> tuple[float, float] | None:
    """Ajusta variacao_selic = alpha + beta*score por OLS, descartando NaN.

    Retorna None se sobrarem menos de 2 observações válidas (OLS de 2
    parâmetros não é identificado com menos que isso).
    """
    mascara = ~np.isnan(score_treino) & ~np.isnan(y_treino)
    if mascara.sum() < 2:
        return None
    x = sm.add_constant(score_treino[mascara])
    resultado = sm.OLS(y_treino[mascara], x).fit()
    alpha, beta = resultado.params
    return alpha, beta


def avaliar_holdout(
    tabela: pd.DataFrame, coluna_score: str, nome_modelo: str, n_teste: int = 6
) -> dict:
    """Calibra no treino (tudo exceto as últimas `n_teste` reuniões) e mede
    RMSE/MAE nas últimas `n_teste` reuniões, fora da amostra de calibração.
    """
    score, y = _preparar_series_ordenadas(tabela, coluna_score)
    n = len(score)
    score_treino, y_treino = score[: n - n_teste], y[: n - n_teste]
    score_teste, y_teste = score[n - n_teste :], y[n - n_teste :]

    ajuste = _ajustar_ols(score_treino, y_treino)
    if ajuste is None:
        return {
            "modelo": nome_modelo,
            "n_treino": 0,
            "n_teste": 0,
            "alpha_hat_treino": float("nan"),
            "beta_hat_treino": float("nan"),
            "rmse_holdout": float("nan"),
            "mae_holdout": float("nan"),
        }
    alpha, beta = ajuste

    previsoes = alpha + beta * score_teste
    mascara_teste = ~np.isnan(previsoes) & ~np.isnan(y_teste)
    erros = y_teste[mascara_teste] - previsoes[mascara_teste]

    n_treino_valido = int((~np.isnan(score_treino) & ~np.isnan(y_treino)).sum())
    return {
        "modelo": nome_modelo,
        "n_treino": n_treino_valido,
        "n_teste": int(mascara_teste.sum()),
        "alpha_hat_treino": alpha,
        "beta_hat_treino": beta,
        "rmse_holdout": float(np.sqrt(np.mean(erros**2))) if len(erros) else float("nan"),
        "mae_holdout": float(np.mean(np.abs(erros))) if len(erros) else float("nan"),
    }


def montar_tabela_holdout(tabela: pd.DataFrame, n_teste: int = 6) -> pd.DataFrame:
    """Roda avaliar_holdout para os modelos presentes na tabela."""
    linhas = [
        avaliar_holdout(tabela, coluna, nome, n_teste=n_teste)
        for coluna, nome in ESPECIFICACOES_MODELOS
        if coluna in tabela.columns
    ]
    return pd.DataFrame(linhas)


def avaliar_walk_forward(
    tabela: pd.DataFrame, coluna_score: str, nome_modelo: str, treino_minimo: int = 20
) -> dict:
    """Janela expansiva: para cada posição t >= treino_minimo, treina OLS nas
    posições [0, t) e prevê a posição t; repete deslizando por toda a
    amostra e agrega RMSE/MAE sobre todas as previsões feitas.
    """
    score, y = _preparar_series_ordenadas(tabela, coluna_score)
    n = len(score)

    erros = []
    for t in range(treino_minimo, n):
        if np.isnan(score[t]) or np.isnan(y[t]):
            continue
        ajuste = _ajustar_ols(score[:t], y[:t])
        if ajuste is None:
            continue
        alpha, beta = ajuste
        previsao = alpha + beta * score[t]
        erros.append(y[t] - previsao)

    erros_array = np.array(erros)
    return {
        "modelo": nome_modelo,
        "n_pred": len(erros_array),
        "rmse_walk_forward": float(np.sqrt(np.mean(erros_array**2))) if len(erros_array) else float("nan"),
        "mae_walk_forward": float(np.mean(np.abs(erros_array))) if len(erros_array) else float("nan"),
    }


def montar_tabela_walk_forward(tabela: pd.DataFrame, treino_minimo: int = 20) -> pd.DataFrame:
    """Roda avaliar_walk_forward para os modelos presentes na tabela."""
    linhas = [
        avaliar_walk_forward(tabela, coluna, nome, treino_minimo=treino_minimo)
        for coluna, nome in ESPECIFICACOES_MODELOS
        if coluna in tabela.columns
    ]
    return pd.DataFrame(linhas)

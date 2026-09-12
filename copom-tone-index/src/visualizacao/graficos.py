"""Gráficos do Índice de Tom, em plotnine (estilo ggplot) — só os 3 LLMs,
o baseline léxico fica de fora dos dois gráficos por pedido.

Paleta "Análise Macro": os hex abaixo são uma paleta provisória (azul-
marinho / terracota / verde-azulado, look editorial comum em relatórios
macro brasileiros) — não confirmada contra a identidade visual oficial da
Análise Macro, que eu não tenho como verificar aqui. Troque os valores de
PALETA_MODELOS se você tiver a paleta oficial da marca.
"""

from __future__ import annotations

import pandas as pd
from plotnine import (
    aes,
    element_text,
    geom_hline,
    geom_line,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)

PALETA_MODELOS = {
    "Gemini": "#0B3C5D",  # azul-marinho
    "Claude": "#D9782D",  # terracota
    "OpenAI": "#1B998B",  # verde-azulado
}

# Nome da coluna de score na tabela final -> rótulo do modelo nos gráficos.
# O léxico (score_lexico) fica de fora de propósito.
NOMES_COLUNA_SCORE = {
    "score_gemini": "Gemini",
    "score_claude": "Claude",
    "score_openai": "OpenAI",
}

TEMA_PADRAO = theme_minimal() + theme(
    figure_size=(9, 5), plot_title=element_text(weight="bold")
)


def montar_dados_indice_calibrado(
    tabela_final: pd.DataFrame, tabela_calibracao: pd.DataFrame
) -> pd.DataFrame:
    """Traduz o score de cada LLM para p.p. de variação da Selic, usando a
    própria calibração OLS do modelo (alpha_hat + beta_hat*score) — assim
    os três ficam numa escala economicamente interpretável e comparável,
    em vez da escala abstrata -3 a +3. Formato longo (data, modelo,
    valor_pp), o que o plotnine espera para desenhar uma linha por modelo.
    """
    blocos = []
    for coluna_score, nome_modelo in NOMES_COLUNA_SCORE.items():
        if coluna_score not in tabela_final.columns:
            continue
        parametros = tabela_calibracao.loc[tabela_calibracao["modelo"] == nome_modelo]
        if parametros.empty:
            continue
        alpha = parametros["alpha_hat"].iloc[0]
        beta = parametros["beta_hat"].iloc[0]

        bloco = tabela_final[["data", coluna_score]].dropna().copy()
        bloco["modelo"] = nome_modelo
        bloco["valor_pp"] = alpha + beta * bloco[coluna_score]
        blocos.append(bloco[["data", "modelo", "valor_pp"]])

    return pd.concat(blocos, ignore_index=True)


def montar_dados_zscore(tabela_final: pd.DataFrame) -> pd.DataFrame:
    """Padroniza o score de cada LLM em z-score (média 0, desvio 1) — a
    "surpresa de comunicação" de cada ata frente ao histórico do próprio
    modelo. Formato longo (data, modelo, zscore).
    """
    blocos = []
    for coluna_score, nome_modelo in NOMES_COLUNA_SCORE.items():
        if coluna_score not in tabela_final.columns:
            continue
        bloco = tabela_final[["data", coluna_score]].dropna().copy()
        media = bloco[coluna_score].mean()
        desvio = bloco[coluna_score].std(ddof=0)
        bloco["modelo"] = nome_modelo
        bloco["zscore"] = 0.0 if desvio == 0 else (bloco[coluna_score] - media) / desvio
        blocos.append(bloco[["data", "modelo", "zscore"]])

    return pd.concat(blocos, ignore_index=True)


def grafico_indice_tom_calibrado(
    tabela_final: pd.DataFrame, tabela_calibracao: pd.DataFrame
) -> ggplot:
    """Índice de Tom calibrado (p.p. de variação da Selic), uma linha por LLM."""
    dados = montar_dados_indice_calibrado(tabela_final, tabela_calibracao)
    dados["data"] = pd.to_datetime(dados["data"])

    return (
        ggplot(dados, aes(x="data", y="valor_pp", color="modelo"))
        + geom_hline(yintercept=0, linetype="dashed", color="gray")
        + geom_line(size=1)
        + scale_color_manual(values=PALETA_MODELOS)
        + labs(
            title="Índice de Tom calibrado (p.p. de variação da Selic)",
            x="Data da reunião",
            y="Tom calibrado (p.p.)",
            color="Modelo",
        )
        + TEMA_PADRAO
    )


def grafico_zscore_tom(tabela_final: pd.DataFrame) -> ggplot:
    """Z-score do tom (surpresa de comunicação), uma linha por LLM."""
    dados = montar_dados_zscore(tabela_final)
    dados["data"] = pd.to_datetime(dados["data"])

    return (
        ggplot(dados, aes(x="data", y="zscore", color="modelo"))
        + geom_hline(yintercept=0, linetype="dashed", color="gray")
        + geom_line(size=1)
        + scale_color_manual(values=PALETA_MODELOS)
        + labs(
            title="Surpresa de comunicação (z-score do tom)",
            x="Data da reunião",
            y="Z-score do tom",
            color="Modelo",
        )
        + TEMA_PADRAO
    )

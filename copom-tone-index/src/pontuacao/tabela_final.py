"""Monta a tabela final: um score de tom por provedor, por reunião, mais a
variação da Selic decidida naquela reunião — a base para a etapa de
Evaluation (CRISP-DM) e para as tabelas do paper.
"""

from __future__ import annotations

from functools import reduce
from pathlib import Path

import pandas as pd

from coleta.selic import baixar_serie_selic, calcular_variacao_por_reuniao

from .loop_claude import CAMINHO_CACHE_PADRAO as CAMINHO_CACHE_CLAUDE_PADRAO
from .loop_gemini import CAMINHO_CACHE_PADRAO as CAMINHO_CACHE_GEMINI_PADRAO
from .loop_openai import CAMINHO_CACHE_PADRAO as CAMINHO_CACHE_OPENAI_PADRAO

# O léxico não tem um loop_*.py com cache incremental (é cálculo
# instantâneo, recalculado do zero a cada execução — ver lexico.py), mas
# scripts/pontuar_atas_lexico.py grava o resultado nesse mesmo caminho.
CAMINHO_SCORES_LEXICO_PADRAO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "scores_lexico.csv"
)


def _carregar_scores(caminho: Path, nome_coluna: str) -> pd.DataFrame:
    """Lê um cache de scores e renomeia a coluna `score` para o nome do provedor."""
    cache = pd.read_csv(caminho)
    return cache.rename(columns={"score": nome_coluna})[["nro_reuniao", "data", nome_coluna]]


def montar_tabela_final(
    caminho_gemini: Path = CAMINHO_CACHE_GEMINI_PADRAO,
    caminho_claude: Path = CAMINHO_CACHE_CLAUDE_PADRAO,
    caminho_openai: Path = CAMINHO_CACHE_OPENAI_PADRAO,
    caminho_lexico: Path = CAMINHO_SCORES_LEXICO_PADRAO,
) -> pd.DataFrame:
    """Junta os quatro scores (3 LLMs + baseline léxico) por (nro_reuniao, data)
    e soma a variação da Selic.

    O merge é feito por `nro_reuniao` E `data` juntos, de propósito: se a
    data de uma mesma reunião divergir entre as fontes (sinal de que algo
    deu errado na coleta), o merge "outer" deixa isso visível como linhas
    separadas com valores faltantes, em vez de escolher silenciosamente
    qual data usar.
    """
    tabelas = [
        _carregar_scores(caminho_gemini, "score_gemini"),
        _carregar_scores(caminho_claude, "score_claude"),
        _carregar_scores(caminho_openai, "score_openai"),
        _carregar_scores(caminho_lexico, "score_lexico"),
    ]
    tabela = reduce(
        lambda esquerda, direita: esquerda.merge(
            direita, on=["nro_reuniao", "data"], how="outer"
        ),
        tabelas,
    ).sort_values("nro_reuniao").reset_index(drop=True)

    serie_selic = baixar_serie_selic()
    tabela["variacao_selic"] = calcular_variacao_por_reuniao(serie_selic, tabela["data"])

    return tabela[
        [
            "nro_reuniao",
            "data",
            "score_gemini",
            "score_claude",
            "score_openai",
            "score_lexico",
            "variacao_selic",
        ]
    ]

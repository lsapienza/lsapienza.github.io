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


def _carregar_scores(caminho: Path, nome_coluna: str) -> pd.DataFrame | None:
    """Lê um cache de scores e renomeia a coluna `score` para o nome do provedor.

    Retorna None se o arquivo ainda não existe — um provedor sem chave de
    API configurada (ex.: Claude sem ANTHROPIC_API_KEY) simplesmente nunca
    gerou seu cache, e a tabela final deve funcionar normalmente só com os
    provedores que já rodaram, em vez de estourar erro.
    """
    if not caminho.exists():
        return None
    cache = pd.read_csv(caminho)
    return cache.rename(columns={"score": nome_coluna})[["nro_reuniao", "data", nome_coluna]]


def montar_tabela_final(
    caminho_gemini: Path = CAMINHO_CACHE_GEMINI_PADRAO,
    caminho_claude: Path = CAMINHO_CACHE_CLAUDE_PADRAO,
    caminho_openai: Path = CAMINHO_CACHE_OPENAI_PADRAO,
    caminho_lexico: Path = CAMINHO_SCORES_LEXICO_PADRAO,
) -> pd.DataFrame:
    """Junta os scores dos provedores já rodados (até 3 LLMs + baseline léxico)
    por (nro_reuniao, data) e soma a variação da Selic.

    O merge é feito por `nro_reuniao` E `data` juntos, de propósito: se a
    data de uma mesma reunião divergir entre as fontes (sinal de que algo
    deu errado na coleta), o merge "outer" deixa isso visível como linhas
    separadas com valores faltantes, em vez de escolher silenciosamente
    qual data usar. Provedores sem cache ainda gerado (ver
    `_carregar_scores`) ficam de fora da tabela — a coluna correspondente
    simplesmente não aparece, em vez de a função falhar.
    """
    fontes = [
        (caminho_gemini, "score_gemini"),
        (caminho_claude, "score_claude"),
        (caminho_openai, "score_openai"),
        (caminho_lexico, "score_lexico"),
    ]
    tabelas = [_carregar_scores(caminho, nome) for caminho, nome in fontes]
    tabelas_presentes = [tabela for tabela in tabelas if tabela is not None]
    if not tabelas_presentes:
        raise FileNotFoundError(
            "Nenhum cache de score encontrado — rode ao menos um "
            "scripts/pontuar_atas_*.py antes de montar a tabela final."
        )

    tabela = reduce(
        lambda esquerda, direita: esquerda.merge(
            direita, on=["nro_reuniao", "data"], how="outer"
        ),
        tabelas_presentes,
    ).sort_values("nro_reuniao").reset_index(drop=True)

    serie_selic = baixar_serie_selic()
    tabela["variacao_selic"] = calcular_variacao_por_reuniao(serie_selic, tabela["data"])

    colunas_presentes = ["nro_reuniao", "data"]
    colunas_presentes += [nome for _, nome in fontes if nome in tabela.columns]
    colunas_presentes.append("variacao_selic")
    return tabela[colunas_presentes]

"""Loop de inferência da OpenAI com cache incremental em CSV.

Mesma lógica de `loop_gemini.py`/`loop_claude.py`: cache por nro_reuniao
evita reenviar uma ata já pontuada; erro numa ata não derruba as demais; o
CSV só é regravado se houve score novo. `scores_openai_cache.csv` usa as
mesmas colunas (nro_reuniao, data, score) e é alinhado por nro_reuniao com
os caches do Gemini e do Claude, para os três serem comparáveis linha a
linha.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from .openai import criar_modelo_openai
from .prompts import INSTRUCOES_SISTEMA
from .schema import TomAta

CAMINHO_CACHE_PADRAO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "scores_openai_cache.csv"
)
COLUNAS_CACHE = ["nro_reuniao", "data", "score"]

# Erros transitórios do lado do provedor/rede que vale a pena tentar de
# novo (5xx, limite de taxa, falhas de conexão/timeout).
ERROS_TRANSITORIOS_OPENAI = (
    InternalServerError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)

TENTATIVAS_MAXIMAS = 6


def _carregar_cache(caminho: Path) -> pd.DataFrame:
    if caminho.exists():
        return pd.read_csv(caminho)
    return pd.DataFrame(columns=COLUNAS_CACHE)


def _salvar_cache(cache: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cache.sort_values("nro_reuniao").to_csv(caminho, index=False)


def _clip_score(score: float) -> float:
    """Garante score em [-3, 3] mesmo se o modelo extrapolar a instrução."""
    return max(-3.0, min(3.0, score))


def _criar_modelo_com_retry():
    """OpenAI + saída estruturada, com retry/backoff exponencial e jitter."""
    modelo = criar_modelo_openai().with_structured_output(TomAta)
    return modelo.with_retry(
        retry_if_exception_type=ERROS_TRANSITORIOS_OPENAI,
        wait_exponential_jitter=True,
        stop_after_attempt=TENTATIVAS_MAXIMAS,
    )


def pontuar_atas_openai(
    documentos: list[Document], caminho_cache: Path = CAMINHO_CACHE_PADRAO
) -> pd.DataFrame:
    """Pontua o tom de cada ata com a OpenAI, reaproveitando o cache em CSV."""
    cache = _carregar_cache(caminho_cache)
    numeros_em_cache = set(cache["nro_reuniao"])

    modelo = _criar_modelo_com_retry()
    novas_linhas = []
    total = len(documentos)

    for indice, documento in enumerate(documentos, start=1):
        nro_reuniao = documento.metadata["nro_reuniao"]
        data = documento.metadata.get("data")

        if nro_reuniao in numeros_em_cache:
            print(f"[{indice}/{total}] reunião {nro_reuniao}: já em cache, pulando")
            continue

        print(f"[{indice}/{total}] reunião {nro_reuniao}: pontuando com OpenAI...")
        try:
            resultado: TomAta = modelo.invoke(
                [
                    ("system", INSTRUCOES_SISTEMA),
                    ("human", documento.page_content),
                ]
            )
        except Exception as erro:
            # Erro numa ata (mesmo após as tentativas de retry) não deve
            # interromper as demais — registra e segue para a próxima.
            print(f"[{indice}/{total}] reunião {nro_reuniao}: ERRO — {erro}")
            continue

        score = _clip_score(resultado.score)
        print(f"[{indice}/{total}] reunião {nro_reuniao}: score = {score:+.2f}")
        novas_linhas.append({"nro_reuniao": nro_reuniao, "data": data, "score": score})

    if novas_linhas:
        cache = pd.concat([cache, pd.DataFrame(novas_linhas)], ignore_index=True)
        _salvar_cache(cache, caminho_cache)
        print(f"Cache atualizado com {len(novas_linhas)} novo(s) score(s) em {caminho_cache}")
    else:
        print("Nenhum score novo — cache não foi regravado.")

    return cache

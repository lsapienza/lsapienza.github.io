"""Loop de inferência do Gemini com cache incremental em CSV.

Ideia central: pontuar uma ata custa uma chamada de API (dinheiro e tempo).
O cache em `scores_gemini_cache.csv` (colunas nro_reuniao, data, score)
garante que uma ata já pontuada numa execução anterior nunca seja
reenviada ao modelo — só atas com nro_reuniao inédito geram uma chamada
nova. Erro numa ata fica registrado no console e não derruba o loop; o
CSV só é regravado se pelo menos um score novo foi calculado.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from google.genai.errors import ServerError
from langchain_core.documents import Document

from .gemini import criar_modelo_gemini
from .prompts import INSTRUCOES_SISTEMA
from .schema import TomAta

CAMINHO_CACHE_PADRAO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "scores_gemini_cache.csv"
)
COLUNAS_CACHE = ["nro_reuniao", "data", "score"]

# Retry com backoff exponencial e jitter para resistir a ServerError (5xx
# do lado do Gemini) — jitter evita que várias atas com erro simultâneo
# batam na API de novo exatamente no mesmo instante.
TENTATIVAS_MAXIMAS = 6


def _carregar_cache(caminho: Path) -> pd.DataFrame:
    """Carrega o CSV de cache se ele existir; senão, devolve um DataFrame vazio."""
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
    """Gemini + saída estruturada, com retry/backoff exponencial e jitter."""
    modelo = criar_modelo_gemini().with_structured_output(TomAta)
    return modelo.with_retry(
        retry_if_exception_type=(ServerError,),
        wait_exponential_jitter=True,
        stop_after_attempt=TENTATIVAS_MAXIMAS,
    )


def pontuar_atas_gemini(
    documentos: list[Document], caminho_cache: Path = CAMINHO_CACHE_PADRAO
) -> pd.DataFrame:
    """Pontua o tom de cada ata com o Gemini, reaproveitando o cache em CSV.

    `documentos` precisa ter, em cada `Document.metadata`, as chaves
    `nro_reuniao` e `data` (formato produzido por
    `coleta.atas_copom.coletar_atas`). Atas cujo nro_reuniao já está no
    cache são puladas sem chamar a API; só atas inéditas são pontuadas.
    """
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

        print(f"[{indice}/{total}] reunião {nro_reuniao}: pontuando com Gemini...")
        try:
            resultado: TomAta = modelo.invoke(
                [
                    ("system", INSTRUCOES_SISTEMA),
                    ("human", documento.page_content),
                ]
            )
        except Exception as erro:
            # Erro numa ata (mesmo depois das tentativas de retry) não deve
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

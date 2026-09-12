"""Loop de inferência do Claude com cache incremental em CSV.

Mesma lógica de `loop_gemini.py`: cache por nro_reuniao evita reenviar uma
ata já pontuada; erro numa ata não derruba as demais; o CSV só é regravado
se houve score novo. `scores_claude_cache.csv` usa as mesmas colunas
(nro_reuniao, data, score) e é alinhado por nro_reuniao com
`scores_gemini_cache.csv`, para que os dois índices sejam comparáveis
linha a linha.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from anthropic import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OverloadedError,
    ServiceUnavailableError,
)
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from .claude import criar_modelo_claude, mensagem_sistema_com_cache
from .schema import TomAta

CAMINHO_CACHE_PADRAO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "scores_claude_cache.csv"
)
COLUNAS_CACHE = ["nro_reuniao", "data", "score"]

# A Anthropic não tem uma única classe "ServerError" como o google-genai;
# esta tupla cobre os erros transitórios do lado do provedor/rede que vale
# a pena tentar de novo (5xx e falhas de conexão/timeout).
ERROS_TRANSITORIOS_ANTHROPIC = (
    InternalServerError,
    OverloadedError,
    ServiceUnavailableError,
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
    """Claude + saída estruturada, com retry/backoff exponencial e jitter."""
    modelo = criar_modelo_claude().with_structured_output(TomAta)
    return modelo.with_retry(
        retry_if_exception_type=ERROS_TRANSITORIOS_ANTHROPIC,
        wait_exponential_jitter=True,
        stop_after_attempt=TENTATIVAS_MAXIMAS,
    )


def pontuar_atas_claude(
    documentos: list[Document], caminho_cache: Path = CAMINHO_CACHE_PADRAO
) -> pd.DataFrame:
    """Pontua o tom de cada ata com o Claude, reaproveitando o cache em CSV.

    O bloco INSTRUCOES_SISTEMA (via `mensagem_sistema_com_cache`) é
    reenviado igual em toda chamada com `cache_control: ephemeral` — a
    partir da segunda ata, a Anthropic serve esse cabeçalho do cache em
    vez de reprocessá-lo.
    """
    cache = _carregar_cache(caminho_cache)
    numeros_em_cache = set(cache["nro_reuniao"])

    modelo = _criar_modelo_com_retry()
    mensagem_sistema = mensagem_sistema_com_cache()
    novas_linhas = []
    total = len(documentos)

    for indice, documento in enumerate(documentos, start=1):
        nro_reuniao = documento.metadata["nro_reuniao"]
        data = documento.metadata.get("data")

        if nro_reuniao in numeros_em_cache:
            print(f"[{indice}/{total}] reunião {nro_reuniao}: já em cache, pulando")
            continue

        print(f"[{indice}/{total}] reunião {nro_reuniao}: pontuando com Claude...")
        try:
            resultado: TomAta = modelo.invoke(
                [mensagem_sistema, HumanMessage(content=documento.page_content)]
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

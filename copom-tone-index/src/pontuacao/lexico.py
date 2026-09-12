"""Baseline léxico hawkish/dovish para o tom das atas do Copom.

Léxico pequeno de propósito, no espírito das listas de palavras de
Loughran & McDonald e do método de contagem direcional de Apel & Grimaldi
(2012) para atas de banco central: só entram termos que indicam direção
por si (não palavras neutras como "inflação" ou "juros" isoladas, que não
dizem se o tom é de aperto ou afrouxamento).

Este não é um método que compete com os LLMs — é o PISO da literatura de
dicionários: um baseline simples, transparente, determinístico e sem
custo de API, contra o qual medir se os LLMs de fato agregam sinal. Por
ser cálculo instantâneo, não há cache aqui (diferente de gemini/claude/
openai) — cada chamada recalcula na hora.
"""

from __future__ import annotations

import re
import unicodedata

# Termos hawkish: sinalizam preocupação com a inflação e favorecem juros
# mais altos / política monetária mais restritiva.
TERMOS_HAWKISH = [
    "elevação da taxa",
    "elevar a taxa",
    "elevação dos juros",
    "juros mais altos",
    "aperto monetário",
    "política monetária contracionista",
    "viés altista",
    "riscos altistas",
    "pressões inflacionárias",
    "pressão inflacionária",
    "persistência inflacionária",
    "expectativas desancoradas",
    "desancoragem das expectativas",
    "ambiente mais restritivo",
    "cautela adicional",
    "vigilância",
    "deterioração do cenário inflacionário",
    "necessidade de aperto",
    "manter a taxa elevada",
    "prolongar o ciclo de aperto",
]

# Termos dovish: sinalizam conforto com a trajetória da inflação e
# favorecem juros mais baixos / política monetária mais expansionista.
TERMOS_DOVISH = [
    "redução da taxa",
    "reduzir a taxa",
    "redução dos juros",
    "juros mais baixos",
    "afrouxamento monetário",
    "política monetária expansionista",
    "viés baixista",
    "riscos baixistas",
    "convergência da inflação",
    "convergência para a meta",
    "ancoragem das expectativas",
    "expectativas ancoradas",
    "espaço para flexibilização",
    "flexibilização monetária",
    "sinais de acomodação",
    "melhora do cenário inflacionário",
    "moderação das pressões inflacionárias",
    "reduzir o grau de restrição",
    "normalização da política monetária",
    "ciclo de corte",
]


def _normalizar(texto: str) -> str:
    """minúsculas e sem acento, para casar termos mesmo com pequenas variações."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def _contar_termos(texto_normalizado: str, termos: list[str]) -> int:
    total = 0
    for termo in termos:
        padrao = r"\b" + re.escape(_normalizar(termo)) + r"\b"
        total += len(re.findall(padrao, texto_normalizado))
    return total


def pontuar_com_lexico(texto_secoes_a_b: str) -> dict:
    """Pontua o tom de um trecho de ata contando termos hawkish e dovish.

    score = (n_hawkish - n_dovish) / (n_hawkish + n_dovish) — sempre em
    [-1, 1] por construção — reescalado para [-3, 3] multiplicando por 3
    (sem necessidade de clip, ao contrário dos LLMs). Ata sem nenhum termo
    do léxico (n_hawkish = n_dovish = 0) recebe 0.0 (neutro), não um erro.

    Retorna um dict com o score já reescalado e as contagens brutas, para
    que a tabela final possa expor n_hawkish/n_dovish sem precisar
    recalcular.
    """
    texto_normalizado = _normalizar(texto_secoes_a_b)
    n_hawkish = _contar_termos(texto_normalizado, TERMOS_HAWKISH)
    n_dovish = _contar_termos(texto_normalizado, TERMOS_DOVISH)

    if n_hawkish + n_dovish == 0:
        score = 0.0
    else:
        score = 3.0 * (n_hawkish - n_dovish) / (n_hawkish + n_dovish)

    return {"score": score, "n_hawkish": n_hawkish, "n_dovish": n_dovish}

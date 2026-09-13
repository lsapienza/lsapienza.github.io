"""Coleta da série SGS 432 (meta Selic definida pelo Copom) e cálculo da
variação em torno de cada reunião.

Confirmado contra a API real: séries de periodicidade diária (como a 432)
só aceitam uma janela de consulta de no máximo 10 anos por chamada — sem
`dataInicial`/`dataFinal`, a API tenta devolver a série inteira (décadas)
e recusa com 406, retornando essa regra explicada no corpo do erro.
`baixar_serie_selic()` sempre informa os dois parâmetros por isso.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .atas_copom import TIMEOUT_SEGUNDOS, criar_sessao_com_retry

URL_SGS_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"

# Margem confortável antes da 232ª reunião (05/08/2020, escopo mínimo do
# projeto) sem estourar a janela de 10 anos até hoje.
DATA_INICIAL_PADRAO = "01/01/2018"


def baixar_serie_selic(
    data_inicial: str = DATA_INICIAL_PADRAO, data_final: str | None = None
) -> pd.DataFrame:
    """Baixa a série da meta Selic (% a.a.) do SGS 432 entre duas datas.

    `data_inicial`/`data_final` no formato "dd/mm/aaaa", exigido pela API.
    `data_final` default é hoje. Retorna um DataFrame com colunas `data`
    (datetime64) e `valor` (float), ordenado por data. A série é diária,
    mas só muda de valor nos dias em que o Copom decide alterar a meta.
    """
    if data_final is None:
        data_final = date.today().strftime("%d/%m/%Y")

    sessao = criar_sessao_com_retry()
    resposta = sessao.get(
        URL_SGS_SELIC,
        params={"formato": "json", "dataInicial": data_inicial, "dataFinal": data_final},
        timeout=TIMEOUT_SEGUNDOS,
    )
    resposta.raise_for_status()

    serie = pd.DataFrame(resposta.json())
    serie["data"] = pd.to_datetime(serie["data"], format="%d/%m/%Y")
    serie["valor"] = serie["valor"].astype(float)
    return serie.sort_values("data").reset_index(drop=True)


def calcular_variacao_por_reuniao(
    serie_selic: pd.DataFrame, datas_reuniao: pd.Series, dias_apos: int = 10
) -> pd.Series:
    """Calcula, para cada data de reunião, a variação da meta Selic decidida nela.

    variação = (valor vigente `dias_apos` dias depois da reunião) - (valor
    vigente imediatamente antes dela).

    "Antes" é o último valor da série com data estritamente anterior à
    reunião. "Depois" NÃO é "o primeiro valor a partir da data da
    reunião" — testado contra dados reais e sempre dava variação 0,
    porque a série é diária e o dia da própria reunião (e às vezes mais
    alguns) ainda reflete a taxa antiga, já que a mudança de meta leva
    alguns dias para entrar em vigor. Em vez disso, "depois" busca o
    último valor conhecido até `dias_apos` dias após a reunião — folga
    suficiente para garantir que a mudança já entrou em vigor, sem
    alcançar a reunião seguinte (o Copom se reúne a cada ~45 dias).

    Retorna uma Series alinhada por posição a `datas_reuniao` (mesma
    ordem/índice de entrada), não ordenada por data internamente.
    """
    reunioes = pd.DataFrame(
        {
            "_ordem": range(len(datas_reuniao)),
            "data_reuniao": pd.to_datetime(pd.Series(datas_reuniao).reset_index(drop=True)),
        }
    )
    reunioes["data_depois"] = reunioes["data_reuniao"] + pd.Timedelta(days=dias_apos)
    reunioes = reunioes.sort_values("data_reuniao")

    serie_antes = serie_selic.rename(columns={"data": "data_valor", "valor": "valor_antes"})
    serie_depois = serie_selic.rename(columns={"data": "data_valor", "valor": "valor_depois"})

    com_antes = pd.merge_asof(
        reunioes,
        serie_antes,
        left_on="data_reuniao",
        right_on="data_valor",
        direction="backward",
        allow_exact_matches=False,
    )
    com_ambos = pd.merge_asof(
        com_antes.sort_values("data_depois"),
        serie_depois,
        left_on="data_depois",
        right_on="data_valor",
        direction="backward",
    )

    com_ambos["variacao_selic"] = com_ambos["valor_depois"] - com_ambos["valor_antes"]
    return com_ambos.sort_values("_ordem")["variacao_selic"].reset_index(drop=True)

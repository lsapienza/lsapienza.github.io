"""Coleta das atas do Copom via API pública do Banco Central.

AVISO IMPORTANTE — leia antes de usar:
Este módulo foi escrito num ambiente sem acesso de rede a bcb.gov.br, então os
nomes de campo do JSON retornado pelas duas APIs (lista e detalhes) NÃO foram
confirmados contra uma resposta real. Cada extração de campo abaixo tenta
várias variações plausíveis de nome de chave (`_obter_campo` é tolerante a
maiúsculas/minúsculas e a sinônimos comuns), mas isso é uma defesa, não uma
confirmação. Antes de rodar a coleta de verdade, execute
`scripts/inspecionar_api_atas.py` (que só funciona com rede liberada para
bcb.gov.br) e confira se as chaves candidatas usadas aqui realmente aparecem
na resposta; ajuste as listas de candidatos se não baterem. Nenhum número ou
texto de ata deste módulo deve ser citado no paper sem ter passado por essa
confirmação.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL_LISTA = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas"
URL_DETALHES = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes"

# A partir da 232ª reunião, conforme escopo definido para o projeto.
REUNIAO_MINIMA = 232

TIMEOUT_SEGUNDOS = 30

# Marcadores de início/fim das seções A e B, usados por extrair_secoes_a_b.
PADRAO_INICIO_SECAO_A = re.compile(r"A\)\s*Atualiza", re.IGNORECASE)
PADRAO_INICIO_SECAO_C = re.compile(
    r"C\)\s*(?:Discuss\w*|Decis\w*|Voto\w*|Condu\w*)", re.IGNORECASE
)
LIMITE_CARACTERES_SECOES_A_B = 4500


def _criar_sessao() -> requests.Session:
    """Cria uma sessão requests com retry e backoff exponencial.

    5 tentativas, backoff_factor=1 → espera 1s, 2s, 4s, 8s, 16s entre elas,
    reagindo a erros transitórios (429 e 5xx) do lado do BCB.
    """
    sessao = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adaptador = HTTPAdapter(max_retries=retry)
    sessao.mount("https://", adaptador)
    sessao.mount("http://", adaptador)
    return sessao


def _obter_campo(item: dict, *candidatos: str) -> Any:
    """Busca um campo em `item` tentando várias grafias possíveis do nome da chave.

    Necessário porque não confirmamos o schema real da API nesta sandbox —
    ver aviso no topo do módulo.
    """
    chaves_normalizadas = {chave.lower(): chave for chave in item}
    for candidato in candidatos:
        chave_real = chaves_normalizadas.get(candidato.lower())
        if chave_real is not None:
            return item[chave_real]
    return None


def _extrair_lista(payload: Any) -> list[dict]:
    """Localiza a lista de reuniões dentro do envelope JSON da API de listagem."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for chave in ("conteudo", "Conteudo", "content", "Content", "items", "Items"):
            valor = payload.get(chave)
            if isinstance(valor, list):
                return valor
    raise ValueError(
        "Formato inesperado na resposta de listagem de atas — "
        "rode scripts/inspecionar_api_atas.py e ajuste _extrair_lista."
    )


@dataclass
class ReuniaoCopom:
    numero_reuniao: int
    data: str | None
    item_bruto: dict


def listar_reunioes(
    sessao: requests.Session,
    a_partir_de: int = REUNIAO_MINIMA,
    quantidade: int = 1000,
) -> list[ReuniaoCopom]:
    """Lista as reuniões do Copom a partir do número mínimo informado."""
    resposta = sessao.get(
        URL_LISTA, params={"quantidade": quantidade}, timeout=TIMEOUT_SEGUNDOS
    )
    resposta.raise_for_status()
    itens = _extrair_lista(resposta.json())

    reunioes = []
    for item in itens:
        numero = _obter_campo(
            item, "NumeroReuniao", "numeroReuniao", "numero_reuniao", "Reuniao", "reuniao"
        )
        if numero is None:
            continue
        numero = int(numero)
        if numero < a_partir_de:
            continue
        data = _obter_campo(
            item, "DataReferencia", "dataReferencia", "data_referencia", "Data", "data"
        )
        reunioes.append(ReuniaoCopom(numero_reuniao=numero, data=data, item_bruto=item))

    reunioes.sort(key=lambda r: r.numero_reuniao)
    return reunioes


def _url_detalhe_da_listagem(item_bruto: dict) -> str | None:
    """Se o item da listagem já traz uma URL de detalhe, usa-a diretamente."""
    return _obter_campo(item_bruto, "Url", "url", "UrlDetalhe", "urlDetalhe")


def buscar_html_ata(sessao: requests.Session, reuniao: ReuniaoCopom) -> str:
    """Baixa o HTML bruto da ata de uma reunião.

    Prioriza uma URL de detalhe já presente no item da listagem; na ausência
    dela, cai para uma chamada a `atas_detalhes` com `numeroReuniao` como
    parâmetro — nome de parâmetro não confirmado nesta sandbox, ajustar
    conforme scripts/inspecionar_api_atas.py.
    """
    url_direta = _url_detalhe_da_listagem(reuniao.item_bruto)
    if url_direta:
        url_completa = (
            url_direta if url_direta.startswith("http") else f"https://www.bcb.gov.br{url_direta}"
        )
        resposta = sessao.get(url_completa, timeout=TIMEOUT_SEGUNDOS)
    else:
        resposta = sessao.get(
            URL_DETALHES,
            params={"numeroReuniao": reuniao.numero_reuniao},
            timeout=TIMEOUT_SEGUNDOS,
        )
    resposta.raise_for_status()

    payload = resposta.json()
    conteudo = payload.get("conteudo", payload) if isinstance(payload, dict) else {}
    html = _obter_campo(
        conteudo, "TextoAta", "textoAta", "Ata", "ata", "Texto", "texto", "Corpo", "corpo", "HtmlAta"
    )
    if html is None:
        raise ValueError(
            f"Não encontrei o texto da ata da reunião {reuniao.numero_reuniao} no JSON de "
            "detalhes — rode scripts/inspecionar_api_atas.py e ajuste buscar_html_ata."
        )
    return html


def limpar_html_ata(html: str) -> str:
    """Limpa o HTML de uma ata: remove script/style/sup e notas de rodapé, normaliza espaços."""
    sopa = BeautifulSoup(html, "html.parser")

    for tag in sopa(["script", "style", "sup"]):
        tag.decompose()

    # Notas de rodapé costumam vir marcadas por classe/id contendo "nota" ou
    # "footnote" nos sites do BCB; removidas por seletor CSS tolerante.
    for elemento in sopa.select(
        '[class*="footnote"], [id*="footnote"], [class*="nota-rodape"], [id*="nota-rodape"]'
    ):
        elemento.decompose()

    texto = sopa.get_text(separator=" ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extrair_secoes_a_b(
    texto_limpo: str, limite_caracteres: int = LIMITE_CARACTERES_SECOES_A_B
) -> str:
    """Recorta do texto já limpo apenas as seções A e B da ata, descartando C em diante.

    Por que isso corta ~50% dos tokens sem perder sinal informacional: nas
    atas do Copom, as seções A ("Atualização da conjuntura...") e B
    ("Cenários e riscos"/avaliação prospectiva) concentram a análise
    qualitativa — leitura da conjuntura doméstica e externa, cenários e
    riscos para a inflação — que é justamente o material com carga
    hawkish/dovish que o índice de tom tenta medir. A partir da seção C
    ("Condução da política monetária"/decisão/votos), a ata passa a tratar
    a decisão da Selic já anunciada, a votação e formalidades processuais —
    um trecho tipicamente tão longo quanto A+B juntas, mas que repete
    estrutura de reunião para reunião e não acrescenta sinal analítico
    novo. Pior: incluir a seção C exporia a própria decisão de Selic (o
    alvo que o índice de tom será calibrado contra) ao texto que os LLMs
    leem para pontuar o tom, contaminando a avaliação com a resposta.
    Cortar em C reduz o texto por volume sem remover o que é relevante
    para o tom.

    O limite de ~4500 caracteres é uma salvaguarda adicional para atas mais
    longas, não o mecanismo principal de corte (que é o próprio recorte
    A→C).
    """
    correspondencia_inicio = PADRAO_INICIO_SECAO_A.search(texto_limpo)
    inicio = correspondencia_inicio.start() if correspondencia_inicio else 0

    correspondencia_fim = PADRAO_INICIO_SECAO_C.search(texto_limpo, pos=inicio)
    fim = correspondencia_fim.start() if correspondencia_fim else len(texto_limpo)

    secoes_a_b = texto_limpo[inicio:fim].strip()
    return secoes_a_b[:limite_caracteres]


def coletar_atas(a_partir_de: int = REUNIAO_MINIMA) -> list[Document]:
    """Coleta, limpa e empacota as atas do Copom a partir da reunião informada.

    Retorna uma lista de `Document` (langchain_core) com `page_content` já
    limpo e `metadata = {"nro_reuniao": ..., "data": ...}`.
    """
    sessao = _criar_sessao()
    reunioes = listar_reunioes(sessao, a_partir_de=a_partir_de)

    documentos = []
    for reuniao in reunioes:
        html = buscar_html_ata(sessao, reuniao)
        texto_limpo = limpar_html_ata(html)
        documentos.append(
            Document(
                page_content=texto_limpo,
                metadata={"nro_reuniao": reuniao.numero_reuniao, "data": reuniao.data},
            )
        )
    return documentos


if __name__ == "__main__":
    documentos = coletar_atas()
    print(f"{len(documentos)} atas coletadas a partir da reunião {REUNIAO_MINIMA}.")

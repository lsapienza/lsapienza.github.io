"""Coleta das atas do Copom via API pública do Banco Central.

Confirmado contra a API real (não mais suposição defensiva):
- A listagem (`atas`) devolve `nroReuniao`, `dataReferencia` (AAAA-MM-DD),
  `dataPublicacao` e `titulo` — sem nenhum campo de URL/detalhe.
- O conteúdo da ata NÃO vem de um endpoint JSON de detalhes (o endpoint
  `atas_detalhes` do escopo original não existe/não é usado pelo site real
  — retorna 500 para qualquer parâmetro testado). O site publica cada ata
  como **PDF**, com a URL seguindo um padrão estável:
  `/content/copom/atascopom/Copom{nro}-not{AAAAMMDD}{nro}.pdf`, onde a
  data é a própria `dataReferencia` da reunião. Padrão descoberto
  inspecionando o tráfego de rede do site (bcb.gov.br/publicacoes/atascopom)
  e confirmado baixando o PDF de verdade para a 232ª reunião (05/08/2020) e
  para as reuniões 277ª-280ª (2026).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any

import requests
from langchain_core.documents import Document
from pypdf import PdfReader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL_LISTA = "https://www.bcb.gov.br/api/servico/sitebcb/copom/atas"

# A partir da 232ª reunião, conforme escopo definido para o projeto.
REUNIAO_MINIMA = 232

TIMEOUT_SEGUNDOS = 30

# Marcadores de início/fim das seções A e B, usados por extrair_secoes_a_b.
PADRAO_INICIO_SECAO_A = re.compile(r"A\)\s*Atualiza", re.IGNORECASE)
PADRAO_INICIO_SECAO_C = re.compile(
    r"C\)\s*(?:Discuss\w*|Decis\w*|Voto\w*|Condu\w*)", re.IGNORECASE
)
LIMITE_CARACTERES_SECOES_A_B = 4500


def criar_sessao_com_retry() -> requests.Session:
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
    """Busca um campo em `item` tentando várias grafias possíveis do nome da chave."""
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
    raise ValueError("Formato inesperado na resposta de listagem de atas.")


@dataclass
class ReuniaoCopom:
    numero_reuniao: int
    data: str  # "AAAA-MM-DD", formato confirmado de dataReferencia
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
        numero = _obter_campo(item, "nroReuniao", "NumeroReuniao", "numeroReuniao")
        data = _obter_campo(item, "dataReferencia", "DataReferencia")
        if numero is None or data is None:
            continue
        numero = int(numero)
        if numero < a_partir_de:
            continue
        reunioes.append(ReuniaoCopom(numero_reuniao=numero, data=data, item_bruto=item))

    reunioes.sort(key=lambda r: r.numero_reuniao)
    return reunioes


def _montar_url_pdf_ata(reuniao: ReuniaoCopom) -> str:
    """Monta a URL do PDF da ata a partir do padrão confirmado contra o site real."""
    data_compacta = reuniao.data.replace("-", "")
    return (
        "https://www.bcb.gov.br/content/copom/atascopom/"
        f"Copom{reuniao.numero_reuniao}-not{data_compacta}{reuniao.numero_reuniao}.pdf"
    )


def baixar_pdf_ata(sessao: requests.Session, reuniao: ReuniaoCopom) -> bytes:
    """Baixa os bytes do PDF da ata de uma reunião."""
    url_pdf = _montar_url_pdf_ata(reuniao)
    resposta = sessao.get(url_pdf, timeout=TIMEOUT_SEGUNDOS)
    resposta.raise_for_status()
    return resposta.content


def extrair_texto_pdf(conteudo_pdf: bytes) -> str:
    """Extrai o texto de um PDF de ata e normaliza espaços em branco."""
    leitor = PdfReader(io.BytesIO(conteudo_pdf))
    texto = " ".join(pagina.extract_text() or "" for pagina in leitor.pages)
    return re.sub(r"\s+", " ", texto).strip()


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
    """Coleta, extrai e empacota as atas do Copom a partir da reunião informada.

    Retorna uma lista de `Document` (langchain_core) com `page_content` já
    extraído do PDF e `metadata = {"nro_reuniao": ..., "data": ...}`.
    """
    sessao = criar_sessao_com_retry()
    reunioes = listar_reunioes(sessao, a_partir_de=a_partir_de)

    documentos = []
    for reuniao in reunioes:
        conteudo_pdf = baixar_pdf_ata(sessao, reuniao)
        texto_limpo = extrair_texto_pdf(conteudo_pdf)
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

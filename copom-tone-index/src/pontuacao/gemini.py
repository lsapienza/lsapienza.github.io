"""Pontuação de tom de atas do Copom via Gemini, com saída estruturada.

`with_structured_output` faz o próprio LangChain instruir o modelo a
retornar dados no formato do schema Pydantic (via function/tool calling do
provedor) e já validar a resposta contra ele — o resultado é sempre um
`TomAta` de verdade, com `score` garantidamente float no intervalo -3.0 a
3.0, sem precisar extrair o número de um texto livre que o modelo poderia
formatar de qualquer jeito.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from .schema import TomAta

MODELO_GEMINI = "gemini-flash-lite-latest"

PROMPT_SISTEMA = (
    "Você é um analista de política monetária. Leia o trecho de uma ata do "
    "Copom (seções de atualização da conjuntura e de cenários e riscos) e "
    "atribua uma única nota de tom: -3.0 é muito dovish, +3.0 é muito "
    "hawkish, 0 é neutro."
)


def criar_modelo_gemini() -> ChatGoogleGenerativeAI:
    """Cria o chat model do Gemini configurado para pontuação de tom.

    temperature=0 porque esta é uma tarefa de classificação determinística
    (uma nota, não geração de texto criativo) — queremos a resposta mais
    provável do modelo, não variação entre chamadas.
    """
    return ChatGoogleGenerativeAI(model=MODELO_GEMINI, temperature=0)


def pontuar_com_gemini(texto_secoes_a_b: str) -> TomAta:
    """Pontua o tom de um trecho de ata (seções A e B) usando o Gemini.

    `modelo.with_structured_output(TomAta)` amarra o schema à chamada: o
    retorno já vem como uma instância de `TomAta`, não como texto para
    fazer parsing.
    """
    modelo = criar_modelo_gemini()
    modelo_estruturado = modelo.with_structured_output(TomAta)
    return modelo_estruturado.invoke(
        [
            ("system", PROMPT_SISTEMA),
            ("human", texto_secoes_a_b),
        ]
    )


if __name__ == "__main__":
    texto_exemplo = (
        "O Copom avalia que os riscos para a inflação seguem altistas, "
        "reforçando a necessidade de manter a política monetária "
        "contracionista por período prolongado."
    )
    resultado = pontuar_com_gemini(texto_exemplo)
    print(resultado)

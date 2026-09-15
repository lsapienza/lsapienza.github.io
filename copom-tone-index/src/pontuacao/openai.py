"""Pontuação de tom de atas do Copom via OpenAI, com saída estruturada.

Reusa o mesmo schema (`TomAta`) e as mesmas `INSTRUCOES_SISTEMA` usadas
para Gemini e Claude — a mesma instrução nos três provedores, para que a
comparação entre eles isole a variável "modelo".

Diferença dos outros dois: aqui não há nada equivalente ao `cache_control`
explícito da Anthropic. A OpenAI cacheia automaticamente, do lado do
servidor, o prefixo repetido de requisições recentes (prompt caching
implícito) — não existe um parâmetro para marcar isso na chamada, então
não há nada a configurar aqui além do tool calling nativo via
`with_structured_output`.
"""

from langchain_openai import ChatOpenAI

from .prompts import INSTRUCOES_SISTEMA
from .schema import TomAta

MODELO_OPENAI = "gpt-4.1-mini"


def criar_modelo_openai() -> ChatOpenAI:
    """Cria o chat model da OpenAI configurado para pontuação de tom.

    temperature=0 pelo mesmo motivo dos outros dois provedores: é uma
    tarefa de classificação determinística, não geração de texto criativo.
    """
    return ChatOpenAI(model=MODELO_OPENAI, temperature=0)


def pontuar_com_openai(texto_secoes_a_b: str) -> TomAta:
    """Pontua o tom de um trecho de ata (seções A e B) usando a OpenAI."""
    modelo = criar_modelo_openai()
    modelo_estruturado = modelo.with_structured_output(TomAta)
    return modelo_estruturado.invoke(
        [
            ("system", INSTRUCOES_SISTEMA),
            ("human", texto_secoes_a_b),
        ]
    )


if __name__ == "__main__":
    texto_exemplo = (
        "O Copom avalia que os riscos para a inflação seguem altistas, "
        "reforçando a necessidade de manter a política monetária "
        "contracionista por período prolongado."
    )
    resultado = pontuar_com_openai(texto_exemplo)
    print(resultado)

"""Pontuação de tom de atas do Copom via Claude, com saída estruturada.

Reusa o mesmo schema (`TomAta`) e as mesmas `INSTRUCOES_SISTEMA` usadas
para o Gemini, para que a comparação entre modelos isole a variável
"modelo", não a variável "instrução".
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

from .prompts import INSTRUCOES_SISTEMA
from .schema import TomAta

MODELO_CLAUDE = "claude-haiku-4-5"


def criar_modelo_claude() -> ChatAnthropic:
    """Cria o chat model do Claude configurado para pontuação de tom.

    temperature=0 pelo mesmo motivo do Gemini: é uma tarefa de
    classificação determinística, não geração de texto criativo.
    """
    return ChatAnthropic(model=MODELO_CLAUDE, temperature=0)


def mensagem_sistema_com_cache() -> SystemMessage:
    """Monta INSTRUCOES_SISTEMA como SystemMessage com cache_control "ephemeral".

    Isso ativa o prompt caching nativo da Anthropic: como esse bloco é
    idêntico em toda chamada (só o texto da ata, no HumanMessage, muda),
    da segunda chamada em diante ele é lido do cache do lado da Anthropic
    em vez de reprocessado, reduzindo custo de input e latência.
    """
    return SystemMessage(
        content=[
            {
                "type": "text",
                "text": INSTRUCOES_SISTEMA,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )


def pontuar_com_claude(texto_secoes_a_b: str) -> TomAta:
    """Pontua o tom de um trecho de ata (seções A e B) usando o Claude."""
    modelo = criar_modelo_claude()
    modelo_estruturado = modelo.with_structured_output(TomAta)
    return modelo_estruturado.invoke(
        [mensagem_sistema_com_cache(), ("human", texto_secoes_a_b)]
    )


if __name__ == "__main__":
    texto_exemplo = (
        "O Copom avalia que os riscos para a inflação seguem altistas, "
        "reforçando a necessidade de manter a política monetária "
        "contracionista por período prolongado."
    )
    resultado = pontuar_com_claude(texto_exemplo)
    print(resultado)

"""Schema Pydantic da nota de tom atribuída a uma ata do Copom."""

from pydantic import BaseModel, Field


class TomAta(BaseModel):
    """Nota de tom (hawkish/dovish) de uma ata do Copom."""

    # Sem ge/le aqui de propósito: se o LLM extrapolar ligeiramente o
    # intervalo pedido (ex.: -3.2), preferimos aceitar e fazer o clip depois
    # (ver loop_gemini.py) a descartar uma pontuação boa por causa de uma
    # validação rígida na hora de montar o structured output.
    score: float = Field(
        ...,
        description=(
            "Nota de tom da ata numa escala contínua de -3.0 a +3.0: "
            "negativo = dovish (sinaliza afrouxamento monetário), "
            "positivo = hawkish (sinaliza aperto monetário), "
            "zero = neutro (sem viés claro)."
        ),
    )

"""Schema Pydantic da nota de tom atribuída a uma ata do Copom."""

from pydantic import BaseModel, Field


class TomAta(BaseModel):
    """Nota de tom (hawkish/dovish) de uma ata do Copom."""

    score: float = Field(
        ...,
        ge=-3.0,
        le=3.0,
        description=(
            "Nota de tom da ata numa escala contínua de -3.0 a +3.0: "
            "negativo = dovish (sinaliza afrouxamento monetário), "
            "positivo = hawkish (sinaliza aperto monetário), "
            "zero = neutro (sem viés claro)."
        ),
    )

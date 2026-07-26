from typing import Literal

from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    """Modelo psicométrico que define o perfil cognitivo e comportamental de um aluno simulado."""

    name: str = Field(
        ..., description="Identificador único do perfil do aluno simulado"
    )
    knowledge_level: Literal["novice", "intermediate", "advanced"] = Field(
        ..., description="Nível de conhecimento prévio em programação e lógica algorítmica"
    )
    error_propensity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probabilidade (entre 0.0 e 1.0) de o aluno cometer um erro lógico ou estrutural intencional",
    )
    impatience_level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probabilidade de o aluno tentar solicitar a resposta pronta ou desviar da metodologia socrática",
    )
    communication_style: str = Field(
        ...,
        description="Padrão linguístico do aluno: verboso, monossilábico, confuso, altamente técnico ou informal",
    )
    domain_problem: str = Field(
        ...,
        description="O problema prático que o aluno deseja modelar e resolver (ex: 'Sistema de triagem de pronto-socorro')",
    )

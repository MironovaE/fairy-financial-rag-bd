"""
Pydantic-схемы для Fairy Financial RAG.
Совместимо с Pydantic v2 (2.5.3+).
"""

from typing import Annotated
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    StringConstraints,
)

# Типы для лучшей читаемости и переиспользования
NonNegativeInt = Annotated[int, Field(ge=0)]
AgeInt = Annotated[int, Field(ge=0, le=200)]
Currency = Annotated[str, Field(default="золотых")]

class Eligibility(BaseModel):
    """Требования к кандидату на финансовую услугу."""

    min_age: NonNegativeInt
    max_age: int | None = Field(None, ge=0)
    min_income: int | None = Field(None, ge=0)
    citizenship_allowed: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_age_range(self) -> "Eligibility":
        if self.max_age is not None and self.max_age < self.min_age:
            raise ValueError("max_age не может быть меньше min_age")
        return self

class Product(BaseModel):
    """Финансовый продукт (кредит, сберегательный счёт и т.п.)."""

    id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]
    name: str
    type: str
    min_amount: float
    max_amount: float | None = None
    term_months: NonNegativeInt
    interest_rate: float
    currency: Currency
    description: str
    text: str
    eligibility: Eligibility

    @model_validator(mode="after")
    def check_amount_range(self) -> "Product":
        if self.max_amount is not None and self.max_amount < self.min_amount:
            raise ValueError("max_amount не может быть меньше min_amount")
        return self

class Hero(BaseModel):
    """Герой (клиент), подающий заявку на продукт."""

    card_suffix: Annotated[str, StringConstraints(pattern=r"^\d{4}$")]
    name: str
    age: AgeInt
    gender: Annotated[str, StringConstraints(pattern=r"^(мужской|женский)$")]
    income: NonNegativeInt
    citizenship: str
    traits: str | None = None
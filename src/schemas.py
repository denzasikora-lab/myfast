from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field, HttpUrl
from src.enums import Currency


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Currency

    description: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    webhook_url: HttpUrl | None = None

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]):
        if len(v) > 50:
            raise ValueError("Too many metadata fields")
        return v

    @model_validator(mode="after")
    def business_rules(self):
        if self.currency == Currency.RUB and self.amount < 10:
            raise ValueError("Minimum RUB amount is 10")

        if self.currency in {Currency.USD, Currency.EUR} and self.amount > 10_000:
            if not self.metadata:
                raise ValueError("Need declaration (metadata required for large payments)")

        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: Decimal
    currency: Currency
    description: str

    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str

    idempotency_key: str
    webhook_url: HttpUrl | None

    created_at: datetime
    processed_at: datetime | None

    @field_validator("metadata", mode="before")
    def fix_metadata(cls, v):
        if v is None:
            return {}

        if isinstance(v, dict):
            return v

        return dict(v) if hasattr(v, "items") else {}


class PaymentCreateResponse(BaseModel):
    payment_id: str
    status: str
    created_at: datetime


class PaymentEvent(BaseModel):
    payment_id: str
    amount: str
    currency: str
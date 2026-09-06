from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):

    username: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=255
    )


class TransactionCreate(BaseModel):

    amount: Decimal = Field(
        ...,
        gt=0
    )

    currency: str = Field(
        ...,
        min_length=3,
        max_length=3
    )

    merchant: str = Field(
        ...,
        min_length=1,
        max_length=200
    )

    location: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    transaction_time: datetime

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value):

        value = value.upper()

        allowed_currencies = {
            "USD",
            "EUR",
            "GBP",
            "INR"
        }

        if value not in allowed_currencies:

            raise ValueError(
                "Currency must be USD, EUR, GBP, or INR"
            )

        return value
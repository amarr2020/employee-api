"""Pydantic v2 models for Token and Employee data."""

import logging
from datetime import date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime

    @field_validator("expires_at", mode="before")
    @classmethod
    def parse_expires_at(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise ValueError(f"Invalid expires_at format: {v}")

    def is_expired(self) -> bool:
        return datetime.now(self.expires_at.tzinfo) >= self.expires_at


class EmployeeBase(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str
    first_name: str
    last_name: str
    email: EmailStr
    date_of_birth: date
    title: str = ""
    image: str = ""
    address: str = ""
    country: str = ""
    bio: str = ""
    rating: float = 0.0

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_date_of_birth(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            return date.fromisoformat(v)
        raise ValueError(f"Invalid date_of_birth format: {v}")

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                logger.warning(f"Invalid rating value '{v}', defaulting to 0.0")
                return 0.0
        return 0.0

    @model_validator(mode="before")
    @classmethod
    def log_unknown_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            known_fields = {
                "id", "first_name", "last_name", "email", "date_of_birth",
                "title", "image", "address", "country", "bio", "rating"
            }
            unknown = set(data.keys()) - known_fields
            if unknown:
                logger.debug(f"Unknown fields in employee data: {unknown}")
        return data


class Employee(EmployeeBase):
    fetched_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Employee":
        return cls(**data)


class EmployeeResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    date_of_birth: date
    title: str
    image: str
    address: str
    country: str
    bio: str
    rating: float
    fetched_at: datetime

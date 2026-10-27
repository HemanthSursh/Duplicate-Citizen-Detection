"""Strict API contracts; validation is shared with the dashboard."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from citizen.matching import validate


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    full_name: str = Field(min_length=1, max_length=150)
    dob: str = Field(min_length=10, max_length=10)
    phone: str = Field(min_length=7, max_length=40)
    address: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def shared_validation(self):
        values = validate(self.model_dump())
        for name, value in values.items():
            setattr(self, name, value)
        return self


class Candidate(BaseModel):
    record_id: str
    kind: Literal["exact", "probable", "name_review"]
    similarity_score: float
    field_scores: dict[str, float]
    matching_fields: list[str]
    differing_fields: list[str]
    reasons: list[str]
    recommended_next_step: Literal["review", "verify"]


class DuplicateResult(BaseModel):
    phone_number_exists: bool = False
    potential_duplicates: bool
    candidates: list[Candidate]
    recommended_next_step: Literal["continue", "review"]


class RegistrationResult(DuplicateResult):
    status: Literal["registered", "review_required", "phone_duplicate"]
    record_id: str | None = None
    detail: str | None = None

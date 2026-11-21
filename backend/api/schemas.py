"""Contratos de dados e esquemas de requisição/resposta."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    data: dict[str, Any]
    model: dict[str, Any]

    @field_validator("data", "model")
    @classmethod
    def validate_subconfigs(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("deve ser um dicionário")
        return v


class RunStatus(BaseModel):
    run_id: UUID
    name: str
    status: Literal["queued", "running", "done", "canceled", "failed"]
    created_at: str


class RunDetail(RunStatus):
    target: str
    config: dict[str, Any]
    metrics: dict[str, Any] | None = None
    n_features: int | None = None
    n_train: int | None = None
    duration_s: float | None = None
    error: str | None = None

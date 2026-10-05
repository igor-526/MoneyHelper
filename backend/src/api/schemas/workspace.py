from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceName(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name не может быть пустым")
        return stripped


class WorkspaceCreate(WorkspaceName):
    currency_id: UUID


class WorkspaceUpdate(WorkspaceName):
    currency_id: UUID | None = None


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    currency_id: UUID
    created_at: datetime
    updated_at: datetime | None

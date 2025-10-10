from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TagLabel = Annotated[str, Field(min_length=1, max_length=60)]
NoteType = Literal["FLEETING", "LITERATURE", "PERMANENT", "INDEX"]


class AddCardRequest(BaseModel):
    """Payload schema for creating a new memory card."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    noteType: NoteType
    body: str | None = Field(default=None, max_length=4000)
    tags: list[TagLabel] | None = Field(default=None, max_length=20)
    originConversationId: str | None = None
    originMessageExcerpt: str | None = Field(default=None, max_length=280)
    sourceReference: str | None = Field(default=None, max_length=2048)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if any(not tag for tag in value):
            raise ValueError("Tags must not be empty")
        if any(len(tag) > 60 for tag in value):
            raise ValueError("Tags must be 60 characters or fewer")
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value


class AddCardResponse(BaseModel):
    """Response schema returned after creating a memory card."""

    model_config = ConfigDict(extra="forbid")

    cardId: str = Field(description="ULID")
    createdAt: str = Field(description="ISO 8601 date-time")
    merged: bool
    noteType: NoteType = Field(description="Note category applied to the card")
    sourceReference: str | None = Field(
        default=None,
        description="Optional citation or provenance reference",
    )
    canonicalCardId: str | None = Field(
        default=None,
        description="Present when merged, pointing to surviving card",
    )
    warnings: list[str] | None = Field(
        default=None,
        description="Optional warnings providing follow-up guidance",
    )


class AddCardError(BaseModel):
    """Error schema for add card tool."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["VALIDATION_ERROR", "STORAGE_FAILURE"]
    message: str


class ManagePayload(BaseModel):
    """Payload schema for update operations."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, max_length=4000)
    tags: list[TagLabel] | None = Field(
        default=None,
        max_length=20,
        json_schema_extra={"uniqueItems": True},
    )
    noteType: NoteType | None = None
    sourceReference: str | None = Field(default=None, max_length=2048)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value


class ManageRequest(BaseModel):
    """Request schema for managing cards."""

    model_config = ConfigDict(extra="forbid")

    cardId: str = Field(min_length=1)
    operation: Literal["UPDATE", "ARCHIVE", "DELETE"]
    payload: ManagePayload | None = None

    @field_validator("cardId")
    @classmethod
    def _strip_card_id(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("cardId must contain at least 1 character")
        return clean

    @model_validator(mode="after")
    def _require_payload_for_update(self) -> "ManageRequest":
        if self.operation == "UPDATE" and self.payload is None:
            raise ValueError("payload is required when operation is UPDATE")
        return self


class ManageResponse(BaseModel):
    """Response schema for manage tool."""

    model_config = ConfigDict(extra="forbid")

    cardId: str
    status: Literal["UPDATED", "ARCHIVED", "DELETED"]
    updatedAt: str | None = Field(default=None, description="ISO 8601 date-time")


class ManageError(BaseModel):
    """Error schema for manage tool."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["NOT_FOUND", "VALIDATION_ERROR", "STORAGE_FAILURE"]
    message: str


class RecallRequest(BaseModel):
    """Payload schema for recalling memory cards."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, max_length=200)
    tags: list[TagLabel] | None = Field(
        default=None,
        max_length=5,
        json_schema_extra={"uniqueItems": True},
    )
    limit: int = Field(default=10, ge=1, le=25)
    includeArchived: bool = Field(default=False)

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len({tag for tag in value}) != len(value):
            raise ValueError("Tags must be unique")
        return value


class RecallCard(BaseModel):
    """Card entry returned by recall tool."""

    model_config = ConfigDict(extra="forbid")

    cardId: str
    title: str
    summary: str
    noteType: NoteType
    rankScore: float
    updatedAt: str
    recallCount: int
    body: str | None = None
    tags: list[str] = Field(default_factory=list)
    sourceReference: str | None = None
    lastRecalledAt: str | None = None


class RecallResponse(BaseModel):
    """Response schema for recall tool."""

    model_config = ConfigDict(extra="forbid")

    cards: list[RecallCard]
    message: str | None = Field(
        default=None,
        description="Friendly message when cards array is empty",
    )


class RecallError(BaseModel):
    """Error schema for recall tool."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["VALIDATION_ERROR", "STORAGE_FAILURE"]
    message: str


class ExportRequest(BaseModel):
    """Payload schema for export tool."""

    model_config = ConfigDict(extra="forbid")

    destinationPath: str | None = Field(
        default=None,
        description="Optional absolute path override for export file",
    )


class ExportResponse(BaseModel):
    """Response schema for export tool."""

    model_config = ConfigDict(extra="forbid")

    filePath: str
    exportedCount: int = Field(ge=0)


class ExportError(BaseModel):
    """Error schema for export tool."""

    model_config = ConfigDict(extra="forbid")

    code: Literal["EXPORT_FAILED"]
    message: str

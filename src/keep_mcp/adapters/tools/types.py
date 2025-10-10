from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


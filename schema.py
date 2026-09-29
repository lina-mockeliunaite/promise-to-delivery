"""Schemas for extraction.

Statement / DocExtraction are the only things the model returns.
StoredStatement is the saved record: the model's fields plus fields the code attaches.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Language = Literal["exploratory", "conditional", "firm"]


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(description="The sentence carrying the commitment, copied word for word from the document.")
    speaker: str = Field(description="Who made the statement.")
    language: Language = Field(description="How firmly the statement is worded.")

    # The API's schema support drops length constraints, so check them here.
    @field_validator("quote", "speaker")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class DocExtraction(BaseModel):
    """Root object of one model reply; an empty list is valid."""

    model_config = ConfigDict(extra="forbid")

    statements: list[Statement]


class StoredStatement(Statement):
    """A statement as saved in a run file. The model supplies none of the extra fields."""

    statement_id: str
    source_id: str
    doc_type: str
    date: str

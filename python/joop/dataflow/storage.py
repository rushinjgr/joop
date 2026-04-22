"""Core storage models for dataflow fallback persistence."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class CachedJSONRecord(SQLModel, table=True):
    """Generic cached JSON payload used by fallback data catchers."""

    id: Optional[int] = Field(default=None, primary_key=True)
    model_type: str
    payload_json: str
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

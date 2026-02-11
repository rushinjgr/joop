"""Core base models for joop SQL-backed types."""

from sqlmodel import SQLModel

class JoopModel(SQLModel):
    """Base SQLModel-derived type for joop-owned models."""

    pass
"""Data catcher abstractions for dataflow."""

from abc import ABCMeta
from dataclasses import dataclass
from typing import ClassVar, Optional, Type

import sqlmodel
from sqlalchemy import func

from joop.abstract import AbstractMethod
from joop.dataflow.capabilities import Capabilities
from joop.sql import SQLConfig


class DataCatcher(metaclass=ABCMeta):
    """Base class for destination resources."""

    capabilities = Capabilities()

    @classmethod
    def get_capabilities(cls) -> Capabilities:
        """Return the declared capabilities for this catcher."""
        return cls.capabilities

    @classmethod
    def replay_to(cls, target_catcher: Type["DataCatcher"], model_type: Type[sqlmodel.SQLModel]):
        """Replay cached records to another catcher.

        This is intentionally catcher-specific and skeletal in v1.
        """
        raise NotImplementedError("Abstract; not implemented")

    replay_to = AbstractMethod(replay_to)

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        """Return how many records this catcher currently has cached."""
        raise NotImplementedError("Abstract; not implemented")

    get_number_of_cached_records = AbstractMethod(get_number_of_cached_records)


@dataclass
class SQLDBDataCatcher(DataCatcher):
    """A scaffold DataCatcher backed by SQL configuration."""

    capabilities = Capabilities(supports_related_models=False)
    sql_config: SQLConfig
    _initialized_table_keys: ClassVar[set[tuple[type, str]]] = set()
    _storage_model_type: ClassVar[Optional[Type[sqlmodel.SQLModel]]] = None

    @classmethod
    def _get_engine(cls):
        """Return the SQLAlchemy engine used by this catcher."""
        return cls.sql_config.get_engine()

    @classmethod
    def _get_table_init_key(cls) -> tuple[type, str]:
        """Return a stable key for one-time table initialization."""
        return (cls, cls.sql_config.get_engine_url())

    @classmethod
    def _ensure_tables(cls):
        """Ensure SQLModel tables are present for this catcher's engine."""
        init_key = cls._get_table_init_key()
        if init_key in cls._initialized_table_keys:
            return
        sqlmodel.SQLModel.metadata.create_all(cls._get_engine())
        cls._initialized_table_keys.add(init_key)

    @classmethod
    def store_model(cls, model: sqlmodel.SQLModel):
        """Persist a model directly to this SQL-backed catcher."""
        cls._ensure_tables()
        with sqlmodel.Session(cls._get_engine()) as session:
            session.merge(model)
            session.commit()
        return "stored"

    @classmethod
    def replay_to(cls, target_catcher: Type[DataCatcher], model_type: Type[sqlmodel.SQLModel]):
        """Replay is catcher-specific; SQL-backed catchers may override this."""
        raise NotImplementedError("Replay is not implemented for this SQLDBDataCatcher.")

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        """Return how many rows currently exist in this catcher's storage model."""
        if cls._storage_model_type is None:
            raise NotImplementedError("SQLDBDataCatcher requires _storage_model_type to count records.")

        cls._ensure_tables()
        statement = sqlmodel.select(func.count()).select_from(cls._storage_model_type)
        with sqlmodel.Session(cls._get_engine()) as session:
            return session.exec(statement).one()

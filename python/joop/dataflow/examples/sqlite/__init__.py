"""

This file contains the first full `joop.dataflow` example for learning,
development, and testing.
Included is an example of a local SQLite-backed dataflow with:
* a primary destination
* a fallback/cache destination
* replay from fallback back to primary

The goal is not to be the most generic implementation possible.
Instead, this example is intentionally concrete and verbose so that it
can serve as the reference point for how the current dataflow abstractions
fit together.

"""

from dataclasses import dataclass, field

from sqlmodel import Field, Session, SQLModel, select

from joop.dataflow import (
    CachedJSONRecord,
    DataFlow,
    DataLink,
    RetryDecision,
    RetryPolicy,
    SQLDBDataCatcher,
)
from joop.sql import SQLConfig, SQLScheme


def _build_sqlite_config(path: str) -> SQLConfig:
    """Build a SQLite SQLConfig for a filesystem path."""
    return SQLConfig(
        scheme=SQLScheme.SQLITE,
        driver=None,
        host="localhost",
        port=None,
        credential=None,
        schema_name=path,
    )
class SQLiteExamplePayload(SQLModel, table=True):
    """Discrete payload model used by the SQLite example flow."""

    # Keep the payload very small on purpose.
    # We are demonstrating the dataflow machinery here, not
    #   a complex domain model.
    # It is also our one canonical model for this dataflow.
    id: int = Field(primary_key=True)
    message: str


@dataclass
class SQLitePrimaryDataCatcher(SQLDBDataCatcher):
    """
    Primary SQLite destination for the example flow.

    This is a real `DataCatcher`, not a mock or placeholder.
    It persists successful deliveries into a local SQLite table.
    """

    # The default path is fine for interactive experimenting, but
    #   tests normally replace it with a temp file.
    sql_config: SQLConfig = field(default_factory=lambda: _build_sqlite_config("sqlite_primary_example.db"))
    _storage_model_type = SQLiteExamplePayload

    @classmethod
    def configure_path(cls, path: str):
        """Set the SQLite path used by this catcher."""
        cls.sql_config = _build_sqlite_config(path)

    @classmethod
    def clear_storage(cls):
        """Remove all delivered rows from the primary destination."""
        cls._ensure_tables()
        with Session(cls._get_engine()) as session:
            rows = session.exec(select(SQLiteExamplePayload)).all()
            for row in rows:
                session.delete(row)
            session.commit()

    @classmethod
    def store_model(cls, model: SQLiteExamplePayload):
        """Persist the canonical payload model to the primary destination."""
        super().store_model(model)
        return "primary-stored"

    @classmethod
    def get_delivered_records(cls) -> list[SQLiteExamplePayload]:
        """Return all delivered rows from the primary destination."""
        cls._ensure_tables()
        with Session(cls._get_engine()) as session:
            return list(session.exec(select(SQLiteExamplePayload)).all())

@dataclass
class SQLiteFallbackDataCatcher(SQLDBDataCatcher):
    """
    Fallback SQLite destination for cached records.

    This catcher acts as the local cache when the primary destination is
    unavailable. Later, replay reads from this store and republishes those
    records into the primary destination.
    """

    sql_config: SQLConfig = field(default_factory=lambda: _build_sqlite_config("sqlite_fallback_example.db"))
    _storage_model_type = CachedJSONRecord

    @classmethod
    def configure_path(cls, path: str):
        """Set the SQLite path used by this fallback catcher."""
        cls.sql_config = _build_sqlite_config(path)

    @classmethod
    def clear_storage(cls):
        """Remove all cached rows from the fallback destination."""
        cls._ensure_tables()
        with Session(cls._get_engine()) as session:
            rows = session.exec(select(CachedJSONRecord)).all()
            for row in rows:
                session.delete(row)
            session.commit()

    @classmethod
    def cache_model(cls, model: SQLiteExamplePayload):
        """Persist a payload as JSON for later replay."""
        cls._ensure_tables()
        with Session(cls._get_engine()) as session:
            session.add(
                CachedJSONRecord(
                    model_type=model.__class__.__name__,
                    payload_json=model.model_dump_json(),
                )
            )
            session.commit()
        return "fallback-cached"

    @classmethod
    def store_model(cls, model: SQLiteExamplePayload):
        """Store a payload in the fallback cache.

        For this catcher, "storing" a model means caching its JSON form for
        later replay rather than inserting the canonical payload table.
        """
        return cls.cache_model(model)

    @classmethod
    def get_cached_records(cls) -> list[CachedJSONRecord]:
        """Return all cached rows waiting for replay."""
        cls._ensure_tables()
        with Session(cls._get_engine()) as session:
            return list(session.exec(select(CachedJSONRecord)).all())

    @classmethod
    def replay_to(cls, target_catcher: "SQLDBDataCatcher", model_type : SQLModel):
        """
        Replay cached rows to the primary catcher and clear them on success.

        Notice where replay logic lives: on the fallback catcher.
        That is intentional for the current `joop.dataflow` design.
        Replay is not assumed to be totally generic; instead, the fallback
        catcher is responsible for knowing how to read its own cached data
        and send it onward.
        """
        cls._ensure_tables()
        target_catcher._ensure_tables()

        replayed_count = 0
        with Session(cls._get_engine()) as session:
            rows = list(session.exec(select(CachedJSONRecord)).all())
            for row in rows:
                # Rebuild the published payload model from the cached JSON.
                model = model_type.model_validate_json(row.payload_json)
                target_catcher.store_model(model)
                # If delivery succeeded, remove it from the cache.
                session.delete(row)
                replayed_count += 1
            session.commit()
        return replayed_count


class SQLiteFallbackPolicy(RetryPolicy):
    """
    Simple retry policy that falls back immediately.

    This is intentionally boring. The point of the example is to show
    fallback and replay, so we skip more elaborate retry behavior.
    """

    @classmethod
    def on_failure(cls, model: SQLModel, attempt_number: int, exception: Exception) -> RetryDecision:
        return RetryDecision.FALLBACK


class LocalSQLiteDataLink(DataLink):
    """
    Concrete SQLite-backed data link for the example flow.

    A `DataLink` is the operational unit in `joop.dataflow`.
    It decides:
    * where the primary destination is
    * where fallback goes
    * which retry policy is used
    * how many cached records exist for replay
    """

    _modeltype = SQLiteExamplePayload
    _catcher_type = SQLitePrimaryDataCatcher
    _retry_policy_type = SQLiteFallbackPolicy
    _fallback_catcher_type = SQLiteFallbackDataCatcher
    primary_should_fail = False

    @classmethod
    def reset(cls):
        """Reset example state for tests or interactive use."""
        cls.primary_should_fail = False

    @classmethod
    def configure_paths(cls, primary_path: str, fallback_path: str):
        """Set the SQLite files used by the example catchers."""
        cls._catcher_type.configure_path(primary_path)
        cls._fallback_catcher_type.configure_path(fallback_path)

    @classmethod
    def _publish_to_catcher(cls, catcher, model: SQLiteExamplePayload):
        # This branch is here only so the example can demonstrate
        #   fallback deterministically in tests and manual experiments.
        if catcher is SQLitePrimaryDataCatcher:
            if cls.primary_should_fail:
                raise RuntimeError("primary SQLite catcher unavailable")
            return catcher.store_model(model)
        return catcher.cache_model(model)


class LocalSQLiteDataFlow(DataFlow):
    """
    DataFlow using a primary and fallback local SQLite destination.

    A `DataFlow` collects one or more links. In this first example there
    is only one link, which keeps the learning surface area manageable.
    """

    _modeltype = SQLiteExamplePayload
    _link_types = [LocalSQLiteDataLink]

    @classmethod
    def configure_paths(cls, primary_path: str, fallback_path: str):
        """Configure the SQLite files used by the example flow."""
        LocalSQLiteDataLink.configure_paths(
            primary_path=primary_path,
            fallback_path=fallback_path,
        )

    @classmethod
    def reset(cls):
        """Reset the example flow state and clear both SQLite stores."""
        LocalSQLiteDataLink.reset()
        SQLitePrimaryDataCatcher.clear_storage()
        SQLiteFallbackDataCatcher.clear_storage()


'''
To use this example in a small script:
```
from joop.dataflow.examples.sqlite import (
    LocalSQLiteDataFlow,
    LocalSQLiteDataLink,
    SQLiteExamplePayload,
)

LocalSQLiteDataFlow.configure_paths(
    primary_path="primary.sqlite",
    fallback_path="fallback.sqlite",
)
LocalSQLiteDataFlow.reset()

# Normal successful publish:
LocalSQLiteDataFlow.publish(
    SQLiteExamplePayload(id=1, message="hello")
)

# Force the primary to fail so fallback is used:
LocalSQLiteDataLink.primary_should_fail = True
LocalSQLiteDataFlow.publish(
    SQLiteExamplePayload(id=2, message="cached for later")
)

# Restore the primary and replay:
LocalSQLiteDataLink.primary_should_fail = False
LocalSQLiteDataFlow.replay()
```
'''

'''
To summarize, this example is made by:
1. Defining a simple payload `SQLModel`.
2. Defining a primary catcher that stores delivered rows.
3. Defining a fallback catcher that stores cached rows.
4. Defining a retry policy that chooses fallback.
5. Defining a `DataLink` that connects those pieces.
6. Defining a `DataFlow` that exposes the link.

Later examples can build on this one by:
* adding multiple links
* changing retry policies
* introducing REST/API-oriented catchers
* handling more complex payload shapes
'''

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from sqlmodel import Session, SQLModel, select

from joop.sql import ORMSQLConfig, SQLScheme


def _build_sqlite_engine_url(path: str) -> str:
    """Build a SQLAlchemy SQLite engine URL from an explicit path choice."""
    if path == "":
        raise ValueError("SQLite path must not be empty.")
    if path == ":memory:":
        return "sqlite:///:memory:"

    resolved_path = Path(path)
    if resolved_path.is_absolute():
        return f"sqlite:///{resolved_path}"
    return f"sqlite:///{resolved_path.as_posix()}"


@dataclass
class SQLiteDB(ORMSQLConfig):
    """SQLite-specific SQL configuration with engine URL behavior."""

    @classmethod
    def from_path(cls, path: str) -> "SQLiteDB":
        """Build a SQLite config from a filesystem path or ``:memory:``."""
        return cls(
            scheme=SQLScheme.SQLITE,
            driver=None,
            host="localhost",
            port=None,
            credential=None,
            schema_name=path,
        )

    @classmethod
    def from_url(cls, url: str) -> "SQLiteDB":
        """Build a SQLite config from a SQLite URL."""
        parsed = urlsplit(url)
        if parsed.scheme == "":
            raise ValueError("SQLiteConfig URL must include a scheme.")

        scheme, driver = cls._parse_scheme_and_driver(parsed.scheme)
        if scheme != SQLScheme.SQLITE:
            raise ValueError("SQLiteConfig.from_url only accepts sqlite URLs.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("SQLite URLs must not include credentials.")
        if parsed.port is not None:
            raise ValueError("SQLite URLs must not include a port.")

        path = parsed.path
        if path == "/:memory:":
            schema_name = ":memory:"
        else:
            schema_name = path if path.startswith("/") else path.lstrip("/")
            if schema_name == "":
                raise ValueError("SQLite URL must include a database path.")

        host = parsed.hostname or "localhost"
        return cls(
            scheme=SQLScheme.SQLITE,
            driver=driver,
            host=host,
            port=None,
            credential=None,
            schema_name=schema_name,
        )

    def __post_init__(self):
        super().__post_init__()
        self.scheme = SQLScheme.SQLITE
        if self.schema_name is None:
            raise ValueError("SQLiteConfig requires schema_name to hold the SQLite path.")

    def get_engine_url(self) -> str:
        """Return the SQLite-specific SQLAlchemy engine URL."""
        return _build_sqlite_engine_url(self.schema_name)

"""
A dataclass for holding SQL connection vars.
"""

from dataclasses import dataclass
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union
from urllib.parse import quote, urlsplit, urlunsplit

from sqlmodel import create_engine
from sqlmodel.main import SQLModelMetaclass
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import registry
from sqlalchemy.exc import SQLAlchemyError

from joop.net import Credential
from joop.sql.model import JoopModel

Host = Union[str, IPv4Address, IPv6Address]
Scheme = Union["SQLScheme", str]

class SQLScheme(str, Enum):
    """Built-in SQL URL schemes supported by joop."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MSSQL = "mssql"
    SQLITE = "sqlite"

@dataclass
class SQLConfig:
    """
    Represents a SQL database connection configuration.

    Attributes:
        scheme (Scheme): The SQL dialect or driver scheme.
        driver (Optional[str]): The adapter or driver name for the scheme.
        host (Host): The hostname or IP address of the SQL server.
            Callers are expected to supply the preferred runtime type directly.
        port (int): The port number to connect to the SQL server.
        credential (Optional[Credential]): The credential used for authentication.
        schema_name (Optional[str]): The name of the database schema (optional).
    """
    scheme: Scheme
    driver: Optional[str]
    host: Host
    port: Optional[int]
    credential: Optional[Credential]
    schema_name: Optional[str]
    
    # _engine : Engine ---- created by get_engine as a singleton

    def __post_init__(self):
        if self.scheme == "":
            raise ValueError("SQLConfig.scheme must not be empty.")
        if self.driver == "":
            raise ValueError("SQLConfig.driver must not be empty when provided.")
        if self.port is not None and not 0 <= self.port <= 65535:
            raise ValueError("SQLConfig.port must be between 0 and 65535.")

    @classmethod
    def from_url(cls, url: str) -> "SQLConfig":
        """Build a SQL configuration from a DSN-style URL."""
        parsed = urlsplit(url)
        if parsed.scheme == "":
            raise ValueError("SQLConfig URL must include a scheme.")

        scheme, driver = cls._parse_scheme_and_driver(parsed.scheme)

        if parsed.hostname is None:
            raise ValueError("SQLConfig URL must include a hostname.")
        if (parsed.username is None) != (parsed.password is None):
            raise ValueError("SQLConfig URL must include both username and password when credentials are present.")

        credential = None
        if parsed.username is not None and parsed.password is not None:
            credential = Credential(username=parsed.username, password=parsed.password)

        schema_name = parsed.path.lstrip("/") or None

        return cls(
            scheme=scheme,
            driver=driver,
            host=parsed.hostname,
            port=parsed.port,
            credential=credential,
            schema_name=schema_name,
        )

    @staticmethod
    def _parse_scheme_and_driver(value: str) -> tuple[Scheme, Optional[str]]:
        """Split a URL scheme into database family and optional driver."""
        scheme_text, separator, driver = value.partition("+")
        scheme: Scheme = scheme_text

        if separator == "":
            return scheme, None
        if driver == "":
            raise ValueError("SQLConfig URL driver must not be empty when '+' is present.")
        return scheme, driver

    @staticmethod
    def _format_host(host: Host) -> str:
        """Format host values for URL serialization."""
        if isinstance(host, IPv6Address):
            return f"[{host.compressed}]"
        return str(host)

    @property
    def url(self) -> str:
        """Serialize the structured SQL config to a DSN-style URL."""
        host = self._format_host(self.host)
        netloc = host
        scheme = self.scheme.value if isinstance(self.scheme, SQLScheme) else self.scheme
        if self.driver is not None:
            scheme = f"{scheme}+{self.driver}"

        if self.credential is not None:
            username = quote(self.credential.username, safe="")
            password = quote(self.credential.password, safe="")
            netloc = f"{username}:{password}@{netloc}"

        if self.port is not None:
            netloc = f"{netloc}:{self.port}"

        path = ""
        if self.schema_name is not None and self.schema_name != "":
            path = f"/{self.schema_name.lstrip('/')}"

        return urlunsplit((scheme, netloc, path, "", ""))

    @property
    def parsed_url(self):
        """Return the stdlib parsed URL view of this config."""
        return urlsplit(self.url)

    @property
    def redacted_url(self) -> str:
        """Serialize the config to a DSN-style URL without credential values."""
        host = self._format_host(self.host)
        netloc = host
        scheme = self.scheme.value if isinstance(self.scheme, SQLScheme) else self.scheme
        if self.driver is not None:
            scheme = f"{scheme}+{self.driver}"

        if self.credential is not None:
            netloc = f"***:***@{netloc}"

        if self.port is not None:
            netloc = f"{netloc}:{self.port}"

        path = ""
        if self.schema_name is not None and self.schema_name != "":
            path = f"/{self.schema_name.lstrip('/')}"

        return urlunsplit((scheme, netloc, path, "", ""))

    def get_engine_url(self) -> str:
        """Return the engine URL for this config."""
        return self.url

    def get_engine(self) -> Engine:
        """Create a SQLAlchemy engine for this config."""
        if getattr(self, "_engine", None) is None:
            self._engine = create_engine(self.get_engine_url())
        return self._engine
    

    def check_accessible(self) -> bool:
        """
        Verify the configured DB is reachable and accepts a simple query.
        """
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return True
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Database is not accessible: {self.redacted_url}") from exc

@dataclass
class ORMSQLConfig(SQLConfig):
    """
    A DB with an associated schema and alembic migrations of a particular arrangement.

    """

    # ---- created in init:
    # _registry : Optional[registry]
    # _metaclass : Optional[SQLModelMetaclass]
    # _basemodel : JoopModel

    def __post_init__(self,):
        super().__post_init__()

        # create a registry

        self._registry = registry()

        # create a metaclass

        self._metaclass = type(
            self.scheme + "MetaClass", # dynamically gen'd class name
            (SQLModelMetaclass,),
            {
                "__abstract__": True,
            },
        )
        
        #  create a basemodel and
        #  set the basemodel metaclass and registry

        self._basemodel = self._metaclass(
            self.scheme + "BaseModel", # dynamically gen'd class name
            (JoopModel,),
            {
                "__module__": __name__,
                "__abstract__": True,
            },
            registry=self._registry,
        )

    # set the basemodel metaclass and registry

    @property
    def basemodel(self):
        return self._basemodel

    # might need to regenerate base when new models added, not sure

    def create_registered_models(self) -> None:
        """
        Create all tables registered on this config's ORM registry.
        """
        engine = self.get_engine()
        self._registry.metadata.create_all(engine)
    
    def check_registered_models_exist(self) -> bool:
        """
        Verify every table in this registry's metadata exists in the DB.
        """
        engine = self.get_engine()
        inspector = inspect(engine)

        missing = []

        for table in self._registry.metadata.sorted_tables:
            schema = table.schema
            table_name = table.name

            if not inspector.has_table(table_name, schema=schema):
                missing.append(f"{schema + '.' if schema else ''}{table_name}")

        if missing:
            raise RuntimeError(
                "Missing database tables for registered models: "
                + ", ".join(missing)
            )
        

        return True
    
    # `*` in function args means `create_missing` must be passed in
    #   by name:
    def bootstrap(self, *, create_missing: bool = True) -> None:
        self.check_accessible()

        if create_missing:
            self.create_registered_models()
        
        self.check_registered_models_exist()

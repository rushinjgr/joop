"""
A simple dataclass for holding SQL connection vars.
"""

from dataclasses import dataclass
from enum import Enum
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Optional, Union
from urllib.parse import quote, urlsplit, urlunsplit

from joop.net import Credential

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

    def __post_init__(self):
        if isinstance(self.scheme, str):
            try:
                self.scheme = SQLScheme(self.scheme)
            except ValueError:
                pass

        if self.scheme == "":
            raise ValueError("SQLConfig.scheme must not be empty.")
        if self.driver == "":
            raise ValueError("SQLConfig.driver must not be empty when provided.")
        if self.port is not None and not 0 <= self.port <= 65535:
            raise ValueError("SQLConfig.port must be between 0 and 65535.")

        if isinstance(self.host, str):
            normalized_host = self._normalize_host(self.host)
            self.host = normalized_host

    @classmethod
    def from_url(cls, url: str) -> "SQLConfig":
        """Build a SQL configuration from a DSN-style URL."""
        parsed = urlsplit(url)
        if parsed.scheme == "":
            raise ValueError("SQLConfig URL must include a scheme.")
        if parsed.hostname is None:
            raise ValueError("SQLConfig URL must include a hostname.")
        if (parsed.username is None) != (parsed.password is None):
            raise ValueError("SQLConfig URL must include both username and password when credentials are present.")

        scheme, driver = cls._parse_scheme_and_driver(parsed.scheme)

        credential = None
        if parsed.username is not None and parsed.password is not None:
            credential = Credential(username=parsed.username, password=parsed.password)

        schema_name = parsed.path.lstrip("/") or None

        return cls(
            scheme=scheme,
            driver=driver,
            host=cls._normalize_host(parsed.hostname),
            port=parsed.port,
            credential=credential,
            schema_name=schema_name,
        )

    @staticmethod
    def _parse_scheme_and_driver(value: str) -> tuple[Scheme, Optional[str]]:
        """Split a URL scheme into database family and optional driver."""
        scheme_text, separator, driver = value.partition("+")
        scheme: Scheme = scheme_text
        try:
            scheme = SQLScheme(scheme_text)
        except ValueError:
            pass

        if separator == "":
            return scheme, None
        if driver == "":
            raise ValueError("SQLConfig URL driver must not be empty when '+' is present.")
        return scheme, driver

    @staticmethod
    def _normalize_host(host: str) -> Host:
        """Normalize an IP host to stdlib IP objects and keep hostnames as strings."""
        try:
            return ip_address(host)
        except ValueError:
            return host

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

@dataclass
class ORMSQLConfig(SQLConfig):
    """
    A DB with an associated schema and alembic migrations of a particular arrangement.

    Attributes:
        db_module_path (str): The path to the database module.
    """
    db_module_path: str

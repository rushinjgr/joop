"""
A simple dataclass for holding SQL connection vars.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class SQLConfig:
    """
    Represents a SQL database connection configuration.

    Attributes:
        host (str): The hostname or IP address of the SQL server.
        port (int): The port number to connect to the SQL server.
        username (str): The username for authentication.
        password (str): The password for authentication.
        schema_name (Optional[str]): The name of the database schema (optional).
    """
    host: str
    port: Optional[int]
    username: str
    password: str
    schema_name: Optional[str]
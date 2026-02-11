"""Networking-related classes for joop.

This module contains foundational networking abstractions that can be shared
across protocol- or service-specific modules.

Classes:
    Credential:
        A simple username/password credential object.
"""

from dataclasses import dataclass

@dataclass
class Credential:
    """A simple username/password credential object."""

    username: str
    password: str

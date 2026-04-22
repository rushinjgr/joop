"""Retry abstractions for dataflow."""

from abc import ABCMeta
from enum import Enum

import sqlmodel

from joop.abstract import AbstractMethod


class RetryDecision(str, Enum):
    """Retry outcomes supported by DataFlow v1."""

    RETRY = "retry"
    FALLBACK = "fallback"


class RetryPolicy(metaclass=ABCMeta):
    """Base class for deciding retry versus fallback after a failure."""

    @classmethod
    def on_failure(
        cls,
        model: sqlmodel.SQLModel,
        attempt_number: int,
        exception: Exception,
    ) -> RetryDecision:
        """Return the next action after a failed publish attempt."""
        raise NotImplementedError("Abstract; not implemented")

    on_failure = AbstractMethod(on_failure)

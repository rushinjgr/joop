"""Flow and link abstractions for dataflow."""

from abc import ABCMeta
from typing import Type

import sqlmodel

from joop.abstract import AbstractMethod
from joop.dataflow.catchers import DataCatcher
from joop.dataflow.retry import RetryDecision, RetryPolicy


class DataLink(metaclass=ABCMeta):
    """Operational connection between a DataFlow and a single DataCatcher."""

    _modeltype: Type[sqlmodel.SQLModel] = None
    _catcher_type: Type[DataCatcher] = None
    _retry_policy_type: Type[RetryPolicy] = None
    _fallback_catcher_type: Type[DataCatcher] = None
    _requires_related_models: bool = False

    @classmethod
    def _check_if_implemented(cls):
        """Ensure required declarative bindings are configured."""
        if (
            cls._modeltype is None or
            cls._catcher_type is None or
            cls._retry_policy_type is None or
            cls._fallback_catcher_type is None
        ):
            raise NotImplementedError("Abstract; not implemented")

    @classmethod
    def _get_primary_catcher(cls) -> Type[DataCatcher]:
        """Return the primary catcher type."""
        return cls._catcher_type

    @classmethod
    def _get_retry_policy(cls) -> Type[RetryPolicy]:
        """Return the retry policy type."""
        return cls._retry_policy_type

    @classmethod
    def _get_fallback_catcher(cls) -> Type[DataCatcher]:
        """Return the fallback catcher type."""
        return cls._fallback_catcher_type

    @classmethod
    def _validate_model(cls, model: sqlmodel.SQLModel):
        """Validate that the provided model matches the bound SQLModel type."""
        if not isinstance(model, cls._modeltype):
            raise TypeError(f"Expected model of type {cls._modeltype.__name__}.")

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: sqlmodel.SQLModel):
        """Publish a model to the provided catcher."""
        raise NotImplementedError("Abstract; not implemented")

    _publish_to_catcher = AbstractMethod(_publish_to_catcher)

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        """Return the number of cached records waiting for replay."""
        fallback_catcher = cls._get_fallback_catcher()
        return fallback_catcher.get_number_of_cached_records()

    @classmethod
    def _check_capability_compatibility(cls):
        """Validate that configured catchers support this link's payload shape."""
        target_capabilities = cls._catcher_type.get_capabilities()
        fallback_capabilities = cls._fallback_catcher_type.get_capabilities()
        if cls._requires_related_models:
            if not target_capabilities.supports_related_models:
                raise TypeError("Primary catcher does not support related SQLModels.")
            if not fallback_capabilities.supports_related_models:
                raise TypeError("Fallback catcher does not support related SQLModels.")

    @classmethod
    def publish(cls, model: sqlmodel.SQLModel):
        """Publish a single SQLModel object through this link."""
        cls._check_if_implemented()
        cls._validate_model(model)
        cls._check_capability_compatibility()

        primary_catcher = cls._get_primary_catcher()
        retry_policy = cls._get_retry_policy()
        fallback_catcher = cls._get_fallback_catcher()

        attempt_number = 0
        while True:
            try:
                return cls._publish_to_catcher(primary_catcher, model)
            except Exception as exc:
                attempt_number += 1
                decision = retry_policy.on_failure(
                    model=model,
                    attempt_number=attempt_number,
                    exception=exc,
                )
                if decision == RetryDecision.RETRY:
                    continue
                if decision == RetryDecision.FALLBACK:
                    return cls._publish_to_catcher(fallback_catcher, model)
                raise ValueError(f"Unsupported retry decision: {decision}")

    @classmethod
    def replay(cls):
        """Replay cached records for this link."""
        cls._check_if_implemented()
        fallback_catcher = cls._get_fallback_catcher()
        primary_catcher = cls._get_primary_catcher()
        return fallback_catcher.replay_to(
            target_catcher=primary_catcher,
            model_type=cls._modeltype,
        )


class DataFlow:
    """Declarative one-way SQLModel dataflow with one or more links."""

    _modeltype: Type[sqlmodel.SQLModel] = None
    _link_types: list[Type[DataLink]] = []

    @classmethod
    def _check_if_implemented(cls):
        """Ensure required declarative bindings are configured."""
        if cls._modeltype is None or len(cls._link_types) == 0:
            raise NotImplementedError("Abstract; not implemented")

    @classmethod
    def _validate_model(cls, model: sqlmodel.SQLModel):
        """Validate that the provided model matches the bound SQLModel type."""
        if not isinstance(model, cls._modeltype):
            raise TypeError(f"Expected model of type {cls._modeltype.__name__}.")

    @classmethod
    def _get_links(cls) -> list[Type[DataLink]]:
        """Return the configured link types for this flow."""
        return cls._link_types

    @classmethod
    def publish(cls, model: sqlmodel.SQLModel):
        """Publish a single SQLModel object through all configured links."""
        cls._check_if_implemented()
        cls._validate_model(model)

        results = []
        for link_type in cls._get_links():
            if link_type._modeltype is not cls._modeltype:
                raise TypeError("DataLink model type must match DataFlow model type.")
            results.append(link_type.publish(model))
        return results

    @classmethod
    def replay(cls):
        """Replay cached records across all configured links."""
        cls._check_if_implemented()

        results = []
        for link_type in cls._get_links():
            if link_type._modeltype is not cls._modeltype:
                raise TypeError("DataLink model type must match DataFlow model type.")
            if link_type.get_number_of_cached_records() > 0:
                results.append(link_type.replay())
        return results

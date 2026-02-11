""" To support a DataFlow, a model must be defined from
        a type in this module.
    While these models are relatively primitive,
        they provide features necessary for a DatFlow
            (ex. primary keying (that stays the same
                between a local cache and remote)).
    Tracking of DataFlow specific metadata is also implemented here.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Type, ClassVar
from uuid import UUID, uuid4

from sqlmodel import Field

from joop.sql.model import JoopModel

class FlowModel(JoopModel, table=False):
    """Base model type for all payloads and storage models used by joop.dataflow."""
    __abstract__ = True

    @classmethod
    def get_model_name(cls) -> str:
        """Return the canonical logical name for this flow model family."""
        model_name = cls.__name__.lstrip("_")
        if model_name == "":
            raise ValueError("FlowModel subclasses must have a usable class name.")
        return model_name

    @classmethod
    def get_primary_model_name(cls) -> str:
        """Return the canonical name used for shared primary storage."""
        return cls.get_model_name()

    @classmethod
    def get_primary_model_class_name(cls, namespace: str | None = None) -> str:
        """Return the concrete class name used for shared primary storage."""
        model_name = cls.get_primary_model_name()
        if namespace is not None and namespace != "":
            return f"{namespace}_{model_name}"
        return model_name

    @classmethod
    def get_primary_model_table_name(cls) -> str:
        """Return the table name used for shared primary storage."""
        return cls.get_primary_model_name().lower()

    @classmethod
    def get_bound_model_class_name(cls, data_catcher_type: type[object]) -> str:
        """Compatibility wrapper for shared primary model naming."""
        return cls.get_primary_model_class_name()

    @classmethod
    def get_bound_model_table_name(cls, data_catcher_type: type[object]) -> str:
        """Compatibility wrapper for shared primary table naming."""
        return cls.get_primary_model_table_name()

    @classmethod
    def get_cache_model_name(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> str:
        """Return the canonical cache-model name for this flow model family."""
        model_name = cls.get_primary_model_name()
        if data_catcher_type is not None:
            return f"{data_catcher_type.__name__}{model_name}"
        return model_name

    @classmethod
    def get_cache_model_class_name(
            cls,
            data_catcher_type: type[object] | None = None,
            namespace: str | None = None,
            ) -> str:
        """Return the cache model class name for this flow model family."""
        model_name = cls.get_cache_model_name(data_catcher_type=data_catcher_type)

        if namespace is not None and namespace != "":
            return f"{namespace}_{model_name}Cache"
        return f"{model_name}Cache"

    @classmethod
    def get_cache_model_table_name(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> str:
        """Return the table name for this model family's cache records."""
        model_name = cls.get_cache_model_name(data_catcher_type=data_catcher_type)
        return f"{model_name.lower()}_cache"

    @classmethod
    def get_cache_model(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> Type["FlowModel"]:
        raise NotImplementedError(f"Use a child class.")

    @classmethod
    def get_cache_model_base(cls) -> Type["FlowModel"]:
        raise NotImplementedError(f"Use a child class.")

class PrimaryFlowModel(FlowModel, table=False):
    """Shared primary-record metadata for inbound and outbound flow models."""

    __abstract__ = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InboundFlowModel(PrimaryFlowModel, table=False):
    """Primary-only flow model for inbound data.

    Inbound records are persisted directly and reused as fallback state;
    unlike outbound records, they do not imply queue/cache companion tables.
    """

    __abstract__ = True
    received_at: Optional[datetime] = None
    last_viewed: Optional[datetime] = None
    source_timestamp: Optional[datetime] = None

class PrimaryOutboundFlowModel(PrimaryFlowModel, table=False):
    """ Model-level structure for outbound caching."""
    
    __abstract__ = True
    cached_at: Optional[datetime] = None # This means it's not cached
    _cache_model: ClassVar[Type["FlowModelCache"]]
    _cache_model_types: ClassVar[dict[type[object], Type["FlowModelCache"]]]
    _cache_model_base: ClassVar[Type["FlowModelCache"]]

    @classmethod
    def set_cache_model(
            cls,
            cache_model: Type["FlowModelCache"],
            data_catcher_type: type[object] | None = None,
            ) -> None:
        """Register a cache model for this flow model family."""
        if data_catcher_type is None:
            cls._cache_model = cache_model
            return

        cache_model_types = cls.__dict__.get("_cache_model_types")
        if cache_model_types is None:
            inherited_cache_model_types = getattr(cls, "_cache_model_types", {})
            cache_model_types = dict(inherited_cache_model_types)
            cls._cache_model_types = cache_model_types

        cache_model_types[data_catcher_type] = cache_model
        if len(cache_model_types) == 1:
            cls._cache_model = cache_model

    @classmethod
    def get_cache_model(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> Type["FlowModelCache"]:
        if data_catcher_type is not None:
            cache_model_types = getattr(cls, "_cache_model_types", {})
            if data_catcher_type not in cache_model_types:
                raise RuntimeError(
                    f"No cache model is registered for {cls.__name__} on "
                    f"{data_catcher_type.__name__}."
                )
            return cache_model_types[data_catcher_type]

        cache_model_types = getattr(cls, "_cache_model_types", {})
        if len(cache_model_types) == 1:
            return next(iter(cache_model_types.values()))
        if len(cache_model_types) > 1:
            raise RuntimeError(
                f"Multiple cache models are registered for {cls.__name__}; "
                "provide data_catcher_type to disambiguate."
            )
        return cls._cache_model

    @classmethod
    def get_cache_model_base(cls) -> Type["FlowModelCache"]:
        return cls._cache_model_base

class OutboundCacheReason(str, Enum):
    FAIL = "fail" # we tried to send the model live but it failed so we cached
    BUFFER = "buffer" # the model was buffered on purpose for another reason

class CacheStatus(str, Enum):
    # just a placeholder for now
    PLACEHOLDER = ""

class FlowModelCache(FlowModel, table=False):
    """ A base model for cache models, so truncated tables
            with metadata for cached data can be defined."""
    __abstract__ = True
    cached_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    cache_reason : OutboundCacheReason = Field(default=OutboundCacheReason.FAIL)
    cache_status : CacheStatus = Field(default=CacheStatus.PLACEHOLDER)

class OutboundUUIDFlowModelCache(FlowModelCache):
    """Caching for models keyed by a UUID primary key."""
    __abstract__ = True
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class OutboundUUIDModel(PrimaryOutboundFlowModel):
    """Use this to make your own UUID-keyed models!"""
    __abstract__ = True
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    _cache_model_base: ClassVar[Type[FlowModelCache]] = OutboundUUIDFlowModelCache
    _cache_model: ClassVar[Type[FlowModelCache]] = OutboundUUIDFlowModelCache

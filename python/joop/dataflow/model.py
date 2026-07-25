"""To support a DataFlow, a model must be defined from a type in this module.

While these models are relatively primitive, they provide features necessary
for a DataFlow, such as primary keying that stays the same between a local
queue and a remote store. Tracking of DataFlow-specific metadata is also
implemented here.
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
    def get_queue_model_name(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> str:
        """Return the canonical queue-model name for this flow model family."""
        model_name = cls.get_primary_model_name()
        if data_catcher_type is not None:
            return f"{data_catcher_type.__name__}{model_name}"
        return model_name

    @classmethod
    def get_queue_model_class_name(
            cls,
            data_catcher_type: type[object] | None = None,
            namespace: str | None = None,
            ) -> str:
        """Return the queue model class name for this flow model family."""
        model_name = cls.get_queue_model_name(data_catcher_type=data_catcher_type)

        if namespace is not None and namespace != "":
            return f"{namespace}_{model_name}Queue"
        return f"{model_name}Queue"

    @classmethod
    def get_queue_model_table_name(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> str:
        """Return the table name for this model family's queue records."""
        model_name = cls.get_queue_model_name(data_catcher_type=data_catcher_type)
        return f"{model_name.lower()}_queue"

    @classmethod
    def get_queue_model(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> Type["FlowModel"]:
        raise NotImplementedError(f"Use a child class.")

    @classmethod
    def get_queue_model_base(cls) -> Type["FlowModel"]:
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
    unlike outbound records, they do not imply queue companion tables.
    """

    __abstract__ = True
    received_at: Optional[datetime] = None
    last_viewed: Optional[datetime] = None
    source_timestamp: Optional[datetime] = None

class PrimaryOutboundFlowModel(PrimaryFlowModel, table=False):
    """Model-level structure for outbound queueing."""
    
    __abstract__ = True
    queued_at: Optional[datetime] = None
    _queue_model: ClassVar[Type["FlowModelQueue"]]
    _queue_model_types: ClassVar[dict[type[object], Type["FlowModelQueue"]]]
    _queue_model_base: ClassVar[Type["FlowModelQueue"]]

    @classmethod
    def set_queue_model(
            cls,
            queue_model: Type["FlowModelQueue"],
            data_catcher_type: type[object] | None = None,
            ) -> None:
        """Register a queue model for this flow model family."""
        if data_catcher_type is None:
            cls._queue_model = queue_model
            return

        queue_model_types = cls.__dict__.get("_queue_model_types")
        if queue_model_types is None:
            inherited_queue_model_types = getattr(cls, "_queue_model_types", {})
            queue_model_types = dict(inherited_queue_model_types)
            cls._queue_model_types = queue_model_types

        queue_model_types[data_catcher_type] = queue_model
        if len(queue_model_types) == 1:
            cls._queue_model = queue_model

    @classmethod
    def get_queue_model(
            cls,
            data_catcher_type: type[object] | None = None,
            ) -> Type["FlowModelQueue"]:
        if data_catcher_type is not None:
            queue_model_types = getattr(cls, "_queue_model_types", {})
            if data_catcher_type not in queue_model_types:
                raise RuntimeError(
                    f"No queue model is registered for {cls.__name__} on "
                    f"{data_catcher_type.__name__}."
                )
            return queue_model_types[data_catcher_type]

        queue_model_types = getattr(cls, "_queue_model_types", {})
        if len(queue_model_types) == 1:
            return next(iter(queue_model_types.values()))
        if len(queue_model_types) > 1:
            raise RuntimeError(
                f"Multiple queue models are registered for {cls.__name__}; "
                "provide data_catcher_type to disambiguate."
            )
        return cls._queue_model

    @classmethod
    def get_queue_model_base(cls) -> Type["FlowModelQueue"]:
        return cls._queue_model_base

class OutboundQueueReason(str, Enum):
    FAIL = "fail"
    BUFFER = "buffer"

class QueueStatus(str, Enum):
    PLACEHOLDER = ""

class FlowModelQueue(FlowModel, table=False):
    """A base model for queue models with outbound bookkeeping metadata."""
    __abstract__ = True
    queued_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    queue_reason : OutboundQueueReason = Field(default=OutboundQueueReason.FAIL)
    queue_status : QueueStatus = Field(default=QueueStatus.PLACEHOLDER)

class OutboundUUIDFlowModelQueue(FlowModelQueue):
    """Queue bookkeeping for models keyed by a UUID primary key."""
    __abstract__ = True
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class OutboundUUIDModel(PrimaryOutboundFlowModel):
    """Use this to make your own UUID-keyed models!"""
    __abstract__ = True
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    _queue_model_base: ClassVar[Type[FlowModelQueue]] = OutboundUUIDFlowModelQueue
    _queue_model: ClassVar[Type[FlowModelQueue]] = OutboundUUIDFlowModelQueue

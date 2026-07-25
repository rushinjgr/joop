"""A datacatcher is an abstraction used to front anywhere data goes to rest in a dataflow.."""

from abc import ABCMeta
from typing import Iterator, Optional
from datetime import datetime, timezone

from sqlmodel import Session, select

from joop.abstract import AbstractMethod
from joop.dataflow.model import FlowModel, PrimaryOutboundFlowModel
from joop.sql import ORMSQLConfig


class DataCatcher(metaclass=ABCMeta):
    """Abstract datacatcher."""
    queueing: bool = False
    round_trip: bool = False

    # ---
    # Added dynamically:
    # primary_model_type : FlowModel

    @classmethod
    def get_base_model(cls):
        """Returns a base model which can be used to bind models, via inheritance."""
        raise NotImplementedError("Abstract; not implemented")

    get_base_model = AbstractMethod(get_base_model)

    @classmethod
    def _get_registered_model_types(cls) -> tuple[type[FlowModel], ...]:
        """Return the model types currently registered on this catcher.
            For example, an additonal model may be used to track queued records."""
        raise NotImplementedError("Abstract; not implemented")

    _get_registered_model_types = AbstractMethod(_get_registered_model_types)

    @classmethod
    def set_primary_model(
            cls,
            primary_flow_model: type[FlowModel],
            **kwargs,
            ) -> None:
        """Register the primary model type used by this catcher.
            Heavy class configuration (backup model generation, etc.)
            lives here."""
        raise NotImplementedError("Abstract; not implemented")

    set_primary_model = AbstractMethod(set_primary_model)

    @classmethod
    def get_number_of_primary_records(cls) -> int:
        """Return how many primary payload records this catcher currently has."""
        raise NotImplementedError("Abstract; not implemented")

    get_number_of_primary_records = AbstractMethod(get_number_of_primary_records)

    def __init__(self, *args, **kwargs):
        """Initialize a catcher instance."""
        raise NotImplementedError("Abstract; not implemented")

    __init__ = AbstractMethod(__init__)

    @classmethod
    def _assert_queueing_enabled(cls) -> None:
        """Ensure this catcher explicitly supports queue storage."""
        assert cls.queueing, f"{cls.__name__} does not support local queueing."

    @classmethod
    def send_model(cls, model: FlowModel):
        """Persist or transmit a registered model through this catcher."""
        raise NotImplementedError("Abstract; not implemented")

    send_model = AbstractMethod(send_model)

    @classmethod
    def queue_model(cls, model: FlowModel):
        """Persist a model locally when it must be buffered or queued."""
        raise NotImplementedError("Abstract; not implemented")

    queue_model = AbstractMethod(queue_model)

    @classmethod
    def get_latest_model(cls) -> Optional[FlowModel]:
        """Return the latest stored primary model for this catcher, if any."""
        raise NotImplementedError("Abstract; not implemented")

    get_latest_model = AbstractMethod(get_latest_model)

    @classmethod
    def iter_queued_models(cls) -> Iterator[FlowModel]:
        """Yield queued models in catcher-defined replay order."""
        raise NotImplementedError("Abstract; not implemented")

    iter_queued_models = AbstractMethod(iter_queued_models)

    @classmethod
    def remove_queued_model(cls, model: FlowModel) -> bool:
        """Remove a queued model from this catcher's queue."""
        raise NotImplementedError("Abstract; not implemented")

    remove_queued_model = AbstractMethod(remove_queued_model)

    @classmethod
    def get_number_of_queued_records(cls) -> int:
        """Return how many queued outbound records this catcher currently has."""
        raise NotImplementedError("Abstract; not implemented")

    get_number_of_queued_records = AbstractMethod(get_number_of_queued_records)

    @classmethod
    def exchange_model(
            cls,
            outbound_model: FlowModel,
            inbound_model_type: type[FlowModel],
            ):
        """Send an outbound model and return a response model, if supported."""
        raise NotImplementedError(
            f"{cls.__name__} does not support round-trip model exchange."
        )


class BasicSQLDataCatcher(DataCatcher):
    """A SQL Datacatcher maps a compatible FlowModel to a SQLConfig"""
    queueing: bool = False
    round_trip: bool = False
    
    sql_config: ORMSQLConfig

    # ---
    # Added dynamically:
    # abstract_model_type : FlowModel
    # primary_model_type : FlowModel

    @classmethod
    def get_base_model(cls):
        """ Return the base model of our DB ORM so that
            classes inheriting it can be defined (so that
            they can thus be bound to this DB).
        """
        return cls.sql_config.basemodel

    @classmethod
    def _get_registered_model_types(cls) -> tuple[type[FlowModel], ...]:
        """ Check that we've got a primary model and return it."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        if primary_model_type is None:
            raise RuntimeError("Primary model must be registered before use.")

        return (primary_model_type,)

    @classmethod
    def _get_engine(cls):
        """Return the SQLAlchemy engine used by this catcher."""
        return cls.sql_config.get_engine()

    @classmethod
    def _get_model_namespace(cls) -> str:
        """Return the naming namespace used for generated model types."""
        scheme = getattr(cls.sql_config, "scheme", None)
        if scheme is None:
            return ""
        return getattr(scheme, "value", str(scheme))

    @classmethod
    def _build_model_type(
            cls,
            class_name: str,
            model_bases: tuple[type[FlowModel], ...],
            module_name: str,
            table_name: Optional[str] = None,
            ) -> type[FlowModel]:
        """Build a concrete SQLModel type bound to this catcher's base model."""
        base_model = cls.get_base_model()
        meta = type(base_model)
        attributes = {
            "__module__": module_name,
        }
        if table_name is not None:
            attributes["__tablename__"] = table_name

        return meta(
            class_name,
            model_bases,
            attributes,
            table=True,
        )

    @classmethod
    def _get_model_table_name(cls, model_type: type[FlowModel]) -> Optional[str]:
        """Return the mapped table name for a concrete model, if present."""
        table = getattr(model_type, "__table__", None)
        if table is not None:
            return table.name
        return getattr(model_type, "__tablename__", None)

    @classmethod
    def _get_compatible_primary_model_types(
            cls,
            primary_flow_model: type[FlowModel],
            target_table_name: str,
            ) -> tuple[type[FlowModel], ...]:
        """Return registered primary model candidates compatible with this flow model."""
        base_model = cls.get_base_model()
        compatible_model_types = []

        for mapper in cls.sql_config._registry.mappers:
            mapped_model_type = mapper.class_
            if (not isinstance(mapped_model_type, type) or
                    not issubclass(mapped_model_type, FlowModel) or
                    not issubclass(mapped_model_type, base_model) or
                    cls._get_model_table_name(mapped_model_type) != target_table_name or
                    not issubclass(mapped_model_type, primary_flow_model)):
                continue

            compatible_model_types.append(mapped_model_type)

        return tuple(compatible_model_types)

    @classmethod
    def _resolve_registered_primary_model_type(
            cls,
            primary_flow_model: type[FlowModel],
            target_table_name: str,
            ) -> type[FlowModel] | None:
        """Return an already-registered compatible primary model, if one exists."""
        compatible_model_types = cls._get_compatible_primary_model_types(
            primary_flow_model=primary_flow_model,
            target_table_name=target_table_name,
        )

        if len(compatible_model_types) > 1:
            candidate_names = ", ".join(
                model_type.__name__ for model_type in compatible_model_types
            )
            raise RuntimeError(
                "Multiple registered primary models match "
                f"{primary_flow_model.__name__} on table {target_table_name}: "
                f"{candidate_names}"
            )

        if len(compatible_model_types) == 1:
            return compatible_model_types[0]

        return None

    @classmethod
    def _bind_primary_model_type(
            cls,
            primary_flow_model: type[FlowModel],
            ) -> type[FlowModel]:
        """Bind an abstract FlowModel type to this catcher's SQL base model."""
        base_model = cls.get_base_model()
        target_class_name = primary_flow_model.get_primary_model_class_name()
        target_table_name = primary_flow_model.get_primary_model_table_name()

        existing_primary_model_type = cls._resolve_registered_primary_model_type(
            primary_flow_model=primary_flow_model,
            target_table_name=target_table_name,
        )
        if existing_primary_model_type is not None:
            return existing_primary_model_type

        if issubclass(primary_flow_model, base_model):
            if cls._get_model_table_name(primary_flow_model) == target_table_name:
                return primary_flow_model
            raise RuntimeError(
                "Concrete primary model already bound to this SQLConfig must use "
                f"table {target_table_name} to participate in shared primary storage."
            )

        return cls._build_model_type(
            class_name=target_class_name,
            model_bases=(base_model, primary_flow_model),
            module_name=primary_flow_model.__module__,
            table_name=target_table_name,
        )

    @classmethod
    def _coerce_to_primary_model(cls, model: FlowModel) -> FlowModel:
        registered_model_types = cls._get_registered_model_types()
        if isinstance(model, registered_model_types):
            return model

        abstract_model_type = getattr(cls, "abstract_model_type", None)
        if abstract_model_type is not None and isinstance(model, abstract_model_type):
            return cls.primary_model_type.model_validate(model)

        raise TypeError(
            "BasicSQLDataCatcher.send_model only accepts the registered "
            "primary model type or the abstract model bound to this catcher."
        )

    @classmethod
    def set_primary_model(
            cls,
            primary_flow_model: type[FlowModel],
            **kwargs,
            ) -> None:
        """Bind an abstract FlowModel to this SQL catcher's ORM base model."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        abstract_model_type = getattr(cls, "abstract_model_type", None)
        if primary_model_type is not None:
            if primary_flow_model in (primary_model_type, abstract_model_type):
                return
            raise RuntimeError("Primary model already registered on this catcher.")

        cls.abstract_model_type = primary_flow_model
        cls.primary_model_type = cls._bind_primary_model_type(primary_flow_model)

    @classmethod
    def get_number_of_queued_records(cls) -> int:
        """A basic SQL catcher does not maintain a queue table."""
        cls._get_registered_model_types()
        return 0

    @classmethod
    def get_number_of_primary_records(cls) -> int:
        """Return the total number of primary payload rows."""
        cls._get_registered_model_types()

        with Session(cls._get_engine()) as session:
            primary_rows = session.exec(select(cls.primary_model_type)).all()

        return len(primary_rows)

    def __init__(self, create_missing = False):
        """ Check that the DB is accessible (via network or otherwise)
                and then make sure that the primary model
                exists as tables in the db. If `create_missing` is true,
                then do a sqlalchemy create all."""
        return self.sql_config.bootstrap(create_missing= create_missing)

    @classmethod
    def send_model(cls, model: FlowModel):
        """ For the supplied model, check that it is of a bound type
                and then store it to the DB."""
        bound_model = cls._coerce_to_primary_model(model)

        with Session(cls._get_engine()) as session:
            session.add(bound_model)
            session.commit()
            session.refresh(bound_model)

        return bound_model

    @classmethod
    def queue_model(cls, model: FlowModel):
        """Reject queueing when this SQL catcher is configured as non-queueing."""
        cls._assert_queueing_enabled()
        return cls.send_model(model)

    @classmethod
    def get_latest_model(cls) -> Optional[FlowModel]:
        """Return the latest primary model ordered by created_at."""
        cls._get_registered_model_types()

        with Session(cls._get_engine()) as session:
            statement = (
                select(cls.primary_model_type)
                .order_by(cls.primary_model_type.created_at.desc())
            )
            return session.exec(statement).first()

    @classmethod
    def iter_queued_models(cls) -> Iterator[FlowModel]:
        """A basic SQL catcher has no queue to replay."""
        cls._get_registered_model_types()
        return iter(())

    @classmethod
    def remove_queued_model(cls, model: FlowModel) -> bool:
        """A basic SQL catcher has no queue entries to remove."""
        cls._get_registered_model_types()
        return False


class QueueingSQLDataCatcher(BasicSQLDataCatcher):
    """A SQL Datacatcher maps a compatible FlowModel to a SQL DB
            via a SQLConfig.
        A Queueing SQL Data Catcher generates at least one
            queue table to then track records that have been queued,
            especially in the sense that they will be sent to
            a different Data Catcher (SQL or otherwise)
            at a later time."""
    queueing: bool = True
    round_trip: bool = False

    sql_config: ORMSQLConfig

    @classmethod
    def _get_queue_model_names(
            cls,
            primary_model_type: type[FlowModel],
            override_queue_table_class_name: Optional[str] = None,
            override_queue_table_name: Optional[str] = None,
            ) -> tuple[str, str]:
        """Return the generated class and table names for a queue model."""
        if (override_queue_table_name is not None and
                override_queue_table_class_name is not None):
            return (
                override_queue_table_class_name,
                override_queue_table_name,
            )

        abstract_model_type = getattr(cls, "abstract_model_type", primary_model_type)
        return (
            abstract_model_type.get_queue_model_class_name(
                data_catcher_type=cls,
                namespace=cls._get_model_namespace(),
            ),
            abstract_model_type.get_queue_model_table_name(
                data_catcher_type=cls,
            ),
        )

    @classmethod
    def _get_registered_model_types(cls) -> tuple[type[FlowModel], ...]:
        """Check that we've got a primary and a queue model and return them."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        queue_model_type = getattr(cls, "queue_model_type", None)

        if primary_model_type is None or queue_model_type is None:
            raise RuntimeError("Primary model must be registered before use.")

        return (primary_model_type, queue_model_type)
        
    @classmethod
    def set_primary_model(cls,
            primary_flow_model : type[FlowModel],
            override_queue_table_class_name : Optional[str] = None,
            override_queue_table_name : Optional[str] = None,
            ):
        """Generate a model for the queue table. This will be a thin model,
                not containing all of the data of queued models, but just their
                primary keys and other necessary information. It's a kind of meta table.
            Then, link the primary to the queue model as well.
        """
        primary_model_type = getattr(cls, "primary_model_type", None)
        abstract_model_type = getattr(cls, "abstract_model_type", None)
        queue_model_type = getattr(cls, "queue_model_type", None)
        if queue_model_type is not None:
            if primary_flow_model in (primary_model_type, abstract_model_type):
                return
            raise RuntimeError("Primary model already registered on this catcher.")

        super().set_primary_model(primary_flow_model)
        abstract_model_type = cls.abstract_model_type

        base_model = cls.get_base_model()
        QueueDef = cls.primary_model_type.get_queue_model_base()
        queue_table_class_name, queue_table_name = cls._get_queue_model_names(
            cls.primary_model_type,
            override_queue_table_class_name=override_queue_table_class_name,
            override_queue_table_name=override_queue_table_name,
        )

        # defining the model as inheriting from base
        #   adds it to our ORM automatically :)
        flow_model_queue = cls._build_model_type(
            class_name=queue_table_class_name,
            model_bases=(base_model, QueueDef),
            module_name=cls.primary_model_type.__module__,
            table_name=queue_table_name,
        )

        cls.queue_model_type = flow_model_queue
        cls.primary_model_type.set_queue_model(flow_model_queue, data_catcher_type=cls)
        if abstract_model_type is not cls.primary_model_type:
            abstract_model_type.set_queue_model(flow_model_queue, data_catcher_type=cls)

    @classmethod
    def send_model(cls, model: FlowModel):
        """ For the supplied model, check that it is of a bound type
                and then store it to the DB."""
        registered_model_types = cls._get_registered_model_types()
        if isinstance(model, registered_model_types):
            bound_model = model
        else:
            bound_model = cls._coerce_to_primary_model(model)

        with Session(cls._get_engine()) as session:
            # Unlike add, merge does not make an object persist in a session
            #   so we copy the return
            bound_model = session.merge(bound_model)
            session.commit()
            session.refresh(bound_model)

        return bound_model

    @classmethod
    def queue_model(cls, model: PrimaryOutboundFlowModel):
        """Store the primary model and a queue row for fallback bookkeeping."""
        cls._assert_queueing_enabled()
        if isinstance(model, cls.queue_model_type):
            return cls.send_model(model)

        model.queued_at = datetime.now(timezone.utc)
        local_model = BasicSQLDataCatcher.send_model.__func__(cls, model)
        queue_model = cls.queue_model_type.model_validate(model)
        cls.send_model(queue_model)
        return local_model

    @classmethod
    def get_number_of_queued_records(cls) -> int:
        """Return the total number of queued bookkeeping rows."""
        cls._get_registered_model_types()

        with Session(cls._get_engine()) as session:
            queued_rows = session.exec(select(cls.queue_model_type)).all()

        return len(queued_rows)

    @classmethod
    def get_number_of_primary_records(cls) -> int:
        """Return the total number of primary payload rows."""
        return BasicSQLDataCatcher.get_number_of_primary_records.__func__(cls)

    @classmethod
    def iter_queued_models(cls) -> Iterator[FlowModel]:
        """Yield queued primary models in queue timestamp order.

        Orphaned queue rows are deliberately dropped here instead of raising,
        so replay can continue past stale queue metadata.
        """
        cls._get_registered_model_types()

        with Session(cls._get_engine()) as session:
            queue_statement = select(cls.queue_model_type).order_by(
                cls.queue_model_type.queued_at.asc()
            )
            queue_rows = list(session.exec(queue_statement).all())
            queued_models = []
            removed_orphans = False

            for queue_row in queue_rows:
                primary_model = session.get(cls.primary_model_type, queue_row.id)
                if primary_model is None:
                    session.delete(queue_row)
                    removed_orphans = True
                    continue
                queued_models.append(primary_model)

            if removed_orphans:
                session.commit()

        return iter(queued_models)

    @classmethod
    def remove_queued_model(cls, model: FlowModel) -> bool:
        """Remove the queued row for the given model, if present."""
        cls._get_registered_model_types()
        bound_model = cls._coerce_to_primary_model(model)

        with Session(cls._get_engine()) as session:
            queue_row = session.get(cls.queue_model_type, bound_model.id)
            if queue_row is None:
                return False

            session.delete(queue_row)
            session.commit()

        return True


class CachingSQLDataCatcher(BasicSQLDataCatcher):
    """A non-queueing SQL catcher that keeps the latest inbound row by PK."""

    @classmethod
    def send_model(cls, model: FlowModel):
        """Store inbound data with upsert semantics against the primary table."""
        bound_model = cls._coerce_to_primary_model(model)

        with Session(cls._get_engine()) as session:
            bound_model = session.merge(bound_model)
            session.commit()
            session.refresh(bound_model)

        return bound_model

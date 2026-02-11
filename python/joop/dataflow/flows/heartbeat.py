"""Round-trip flow orchestration built on top of inbound and outbound links."""

import sys
from typing import Optional

from joop.dataflow.flows import DataFlow
from joop.dataflow.catchers import DataCatcher
from joop.dataflow.link import ArtificialDataLink
from joop.dataflow.model import InboundFlowModel, PrimaryOutboundFlowModel


class Heartbeat(DataFlow):
    """Send outbound heartbeat data and persist the returned inbound response."""

    heartbeat_datamodel: type[PrimaryOutboundFlowModel] | None = None
    response_datamodel: type[InboundFlowModel] | None = None
    response_local_type: type[DataCatcher] | None = None
    remote_type: type[InboundFlowModel] | None = None

    def __init__(self, create_missing: bool = False):
        self._configure_inbound_link_type()
        super().__init__(create_missing=create_missing)
        self._bind_datamodels()

    @classmethod
    def _resolve_response_datamodel(cls) -> type[InboundFlowModel]:
        """Resolve the inbound response model used by this heartbeat flow."""
        response_datamodel = cls.response_datamodel
        if response_datamodel is None:
            remote_type = getattr(cls, "remote_type", None)
            if (isinstance(remote_type, type) and
                    issubclass(remote_type, InboundFlowModel)):
                response_datamodel = remote_type

        if response_datamodel is None:
            raise NotImplementedError(
                "Heartbeat requires response_datamodel when "
                "primary_inbound_data_link_type is not defined."
            )

        return response_datamodel

    @classmethod
    def _resolve_response_local_type(cls) -> type[DataCatcher]:
        """Resolve the local catcher used to persist heartbeat responses."""
        response_local_type = cls.response_local_type
        if response_local_type is None:
            local_type = getattr(cls, "local_type", None)
            if isinstance(local_type, type) and issubclass(local_type, DataCatcher):
                response_local_type = local_type
        if response_local_type is None:
            flow_module = sys.modules.get(cls.__module__)
            if flow_module is not None:
                module_local_type = getattr(flow_module, "LocalInboundDataCatcher", None)
                if (isinstance(module_local_type, type) and
                        issubclass(module_local_type, DataCatcher)):
                    response_local_type = module_local_type
        if response_local_type is None:
            raise NotImplementedError(
                "Heartbeat requires response_local_type when "
                "primary_inbound_data_link_type is not defined."
            )

        return response_local_type

    @classmethod
    def _build_artificial_inbound_data_link_type(cls) -> type[ArtificialDataLink]:
        """Build an artificial inbound link type for persisted responses."""
        response_datamodel = cls._resolve_response_datamodel()
        response_local_type = cls._resolve_response_local_type()

        return type(
            f"{cls.__name__}ArtificialInboundDataLink",
            (ArtificialDataLink,),
            {
                "__module__": cls.__module__,
                "datamodel": response_datamodel,
                "local_type": response_local_type,
            },
        )

    @classmethod
    def _configure_inbound_link_type(cls) -> None:
        """Create an artificial inbound link type when one is not supplied."""
        if cls.primary_inbound_data_link_type is not None:
            return
        if (cls.response_datamodel is None and
                not (isinstance(getattr(cls, "remote_type", None), type) and
                     issubclass(cls.remote_type, InboundFlowModel)) and
                cls.response_local_type is None):
            return

        cls.primary_inbound_data_link_type = cls._build_artificial_inbound_data_link_type()

    def _check_if_implemented(self) -> None:
        """Heartbeat flows require both primary inbound and outbound links."""
        super()._check_if_implemented()
        if self.primary_inbound_data_link_type is None:
            raise NotImplementedError(
                "Heartbeat requires a primary inbound data link type."
            )
        if self.primary_outbound_data_link_type is None:
            raise NotImplementedError(
                "Heartbeat requires a primary outbound data link type."
            )

    def _bind_datamodels(self) -> None:
        """Bind heartbeat/response datamodels from the configured primary links."""
        outbound_datamodel = self.primary_outbound_data_link.datamodel
        inbound_datamodel = self.primary_inbound_data_link.datamodel

        if self.heartbeat_datamodel is None:
            self.heartbeat_datamodel = outbound_datamodel
        elif self.heartbeat_datamodel is not outbound_datamodel:
            raise RuntimeError(
                "Heartbeat heartbeat_datamodel must match the primary outbound "
                "data link datamodel."
            )

        if self.response_datamodel is None:
            self.response_datamodel = inbound_datamodel
        elif self.response_datamodel is not inbound_datamodel:
            raise RuntimeError(
                "Heartbeat response_datamodel must match the primary inbound "
                "data link datamodel."
            )

    def _sync(
            self,
            outbound_data: PrimaryOutboundFlowModel,
            ) -> Optional[InboundFlowModel]:
        """Drain outbound backlog, exchange a heartbeat, and store the response."""
        if not isinstance(outbound_data, self.heartbeat_datamodel):
            raise TypeError(
                "Heartbeat.sync only accepts models matching its heartbeat_datamodel."
            )

        # Deliberately stop on the first replay failure so queued ordering
        # remains predictable and the new heartbeat is not sent ahead of backlog.
        for queued_model in self.primary_outbound_data_link.local.iter_queued_models():
            try:
                self.primary_outbound_data_link.remote.send_model(queued_model)
            except Exception:
                return None

            self.primary_outbound_data_link.local.remove_queued_model(queued_model)

        response_model = self.primary_outbound_data_link.exchange(
            outbound_data,
            inbound_model_type=self.response_datamodel,
        )
        if response_model is None:
            return None

        return self.primary_inbound_data_link.accept(response_model)
    
    def _sync(
            self,
            outbound_data: PrimaryOutboundFlowModel,
            ) -> Optional[InboundFlowModel]:
        pass

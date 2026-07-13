''' Represents a link between two DataCatchers.'''
from typing import Type, Optional
from joop.dataflow.catchers import DataCatcher
from joop.dataflow.model import FlowModel, PrimaryOutboundFlowModel, InboundFlowModel

class DataLink:
    ''' Bind a FlowModel, a local DataCatcher, and a Remote
            DataCatcher. Local and remote terminology is used,
            based on the assumption that data flows downstream from
            the first catcher to the second, and that this is done
            primarily for the purpose of caching locally, either to bulk
            sends to a remote datastore or to provide caching (or buffering)
            during times when the remote is unavailable.'''
    datamodel: type[FlowModel] | None = None
    local_datacatcher_type: type[DataCatcher] | None = None
    remote_datacatcher_type: type[DataCatcher] | None = None
    local_caching_required: bool | None = None
    remote_required: bool = True
    local: DataCatcher
    remote: Optional[DataCatcher] = None

    def __init__(
            self,
            datamodel: type[FlowModel] | None = None,
            local_datacatcher_type: type[DataCatcher] | None = None,
            remote_datacatcher_type: type[DataCatcher] | None = None,
            create_missing: bool = False,
            ) -> None:
        """ Also initialize DataCatchers (and all that that implies.
                If `create_missing` is True, then supply that parameter
                down to the datacatcher setup (it applies to SQL DataCatchers)"""
        if datamodel is not None:
            self.datamodel = datamodel
        if local_datacatcher_type is not None:
            self.local_datacatcher_type = local_datacatcher_type
        if remote_datacatcher_type is not None:
            self.remote_datacatcher_type = remote_datacatcher_type

        self._check_if_implemented()        

        # Configure the datacatchers from the shared flow model type.
        self.local_datacatcher_type.set_primary_model(self.datamodel)
        # Instantiate the datacatcher:
        self.local = self._setup_datacatcher(data_catcher_type= self.local_datacatcher_type,
                                             create_missing= create_missing)

        if self.remote_datacatcher_type is not None:
            self.remote_datacatcher_type.set_primary_model(self.datamodel)
            # Instantiate the datacatcher:
            self.remote = self._setup_datacatcher(data_catcher_type= self.remote_datacatcher_type,
                                                 create_missing= create_missing)

    def _check_if_implemented(self) -> None:
        """ Verify that we have a bound model and DataCatcher types."""
        if self.datamodel is None or self.local_datacatcher_type is None:
            raise NotImplementedError(
                "DataLink requires datamodel and local_datacatcher_type to be defined."
            )
        if self.remote_required and self.remote_datacatcher_type is None:
            raise NotImplementedError(
                "DataLink requires remote_datacatcher_type to be defined."
            )
        if (self.local_caching_required is not None and
                self.local_datacatcher_type.caching != self.local_caching_required):
            caching_requirement = "a caching" if self.local_caching_required else "a non-caching"
            raise TypeError(
                f"{self.__class__.__name__} requires {caching_requirement} "
                "local_datacatcher_type DataCatcher."
            )
    
    def _setup_datacatcher(self, data_catcher_type : Type[DataCatcher], create_missing : bool = False) -> DataCatcher:
        """ Initialize the datacatcher. This is done *after* binding the types of
                the DataCatchers and the models that will be used for them."""
        return data_catcher_type(create_missing = create_missing)

    def publish(self, model: FlowModel) -> FlowModel:
        """ Check the given model instance and then
                attempt once to publish it to the remote.
            If this fails, cache the model."""
        
        # TODO add a retry policy class and handle it here

        if not isinstance(model, self.datamodel):
            raise TypeError(
                "DataLink.publish only accepts models matching its datamodel type."
            )

        try:
            return self.remote.send_model(model)
        except Exception:
            return self.local.cache_model(model)

    def get_latest_local(self) -> Optional[FlowModel]:
        """Return the latest locally stored primary model, if any."""
        return self.local.get_latest_model()
    
class InboundDataLink(DataLink):
    """Fetch inbound data from a remote source with local fallback.

    Inbound links treat the local catcher as a store of last-known primary
    records, not as a queue. Fetch attempts remote retrieval first and falls
    back to the latest local primary row when the remote is unavailable or has
    no model to provide.
    """

    # inherited:
    #local: Type[DataCatcher]
    #remote: Type[DataCatcher]
    datamodel : Type[InboundFlowModel]
    local_caching_required = False
    current_model: Optional[InboundFlowModel] = None

    def _fetch(self) -> Optional[InboundFlowModel]:
        """Return the latest inbound model, preferring remote over local.

        The remote catcher is queried first. If that query raises or returns
        no model, the latest local primary row is returned instead.
        """
        try:
            model = self.remote.get_latest_model()
        except Exception:
            model = self.get_latest_local()
        else:
            if model is None:
                model = self.get_latest_local()

        if model is None:
            return None
        if not isinstance(model, self.datamodel):
            raise TypeError(
                "InboundDataLink._fetch only accepts models matching its datamodel type."
            )

        return model

    def fetch(self) -> bool:
        """Fetch and retain the current inbound model.

        Returns ``True`` when the fetched model exists and has never been
        viewed, meaning its ``last_viewed`` field is ``None``. Returns
        ``False`` when no model is available or when the fetched model has
        already been viewed.
        """
        model = self._fetch()
        self.current_model = model
        if model is None:
            return False
        return model.last_viewed is None

    def _accept(self, model: InboundFlowModel) -> InboundFlowModel:
        """Persist a returned inbound model through the local inbound catcher."""
        if not isinstance(model, self.datamodel):
            raise TypeError(
                "InboundDataLink.accept only accepts models matching its datamodel type."
            )

        stored_model = self.local.send_model(model)
        self.current_model = stored_model
        return stored_model

    def accept(self, model: InboundFlowModel) -> InboundFlowModel:
        return self._accept(model)


class ArtificialDataLink(InboundDataLink):
    """An inbound link whose data arrives by local acceptance, not remote fetch.

    This is useful when another flow, such as a heartbeat exchange, produces the
    inbound model directly and only local storage/fallback behavior is needed.
    """

    remote_required = False
    remote_datacatcher_type = None

    def _fetch(self) -> Optional[InboundFlowModel]:
        """Return the latest local inbound model without consulting a remote."""
        model = self.get_latest_local()
        if model is None:
            return None
        if not isinstance(model, self.datamodel):
            raise TypeError(
                "ArtificialDataLink._fetch only accepts models matching its datamodel type."
            )
        return model

class OutBoundDataLink(DataLink):
    # inherited:
    #local_datacatcher_type: type[DataCatcher] | None = None
    #remote_datacatcher_type: type[DataCatcher] | None = None
    #local: DataCatcher
    #remote: DataCatcher

    datamodel : Type[PrimaryOutboundFlowModel]
    local_caching_required = True

    def _queue(self, out):
        # In the case of either fallback
        #   or buffering, queue an outbound
        #   datamodel locally to be transmitted
        #   later.
        if not isinstance(out, self.datamodel):
            raise TypeError(
                "OutBoundDataLink.queue only accepts models matching its datamodel type."
            )
        return self.local.cache_model(out)

    def queue(self, out):
        return self._queue(out)

    def get_queue_length(self):
        # get the number of queued outbound messages
        return self.local.get_number_of_cached_records()
    
    def publish(self, outbound_data : PrimaryOutboundFlowModel):
        # Attempt to _push an outbound datamodel.
        #   In case of failure, _queue.
        return super().publish(outbound_data)

    def exchange(
            self,
            outbound_data: PrimaryOutboundFlowModel,
            inbound_model_type: type[InboundFlowModel],
            ) -> Optional[InboundFlowModel]:
        """Send outbound data and return a response model when supported.

        This is intentionally separate from ``publish`` so one-way outbound
        sends remain simple. If the remote exchange raises, the outbound model
        is queued locally just like a failed publish.
        """
        if not isinstance(outbound_data, self.datamodel):
            raise TypeError(
                "OutBoundDataLink.exchange only accepts models matching its datamodel type."
            )
        if not self.remote_datacatcher_type.round_trip:
            raise RuntimeError(
                "OutBoundDataLink.exchange requires a round-trip "
                "remote_datacatcher_type DataCatcher."
            )

        try:
            inbound_data = self.remote.exchange_model(
                outbound_data,
                inbound_model_type=inbound_model_type,
            )
        except NotImplementedError:
            raise
        except Exception:
            self.local.cache_model(outbound_data)
            return None

        if inbound_data is None:
            return None
        if not isinstance(inbound_data, inbound_model_type):
            raise TypeError(
                "OutBoundDataLink.exchange only accepts response models matching "
                "the requested inbound_model_type."
            )

        return inbound_data

    def sync(self, outbound_data : Optional[PrimaryOutboundFlowModel]):
        # Drain the existing backlog before sending any new outbound data.
        for queued_model in self.local.iter_queued_models():
            try:
                self.remote.send_model(queued_model)
            except Exception:
                # Deliberately stop on the first replay failure so queued
                # ordering remains predictable and later items stay buffered.
                return

            self.local.remove_queued_model(queued_model)

        if outbound_data is not None:
            self.publish(outbound_data)

"""High-level flow orchestration types built on top of data links.

This layer is still intentionally lightweight. For now it mainly enforces
which inbound/outbound link types a flow supports and instantiates those
links consistently.
"""

from typing import Optional

from joop.dataflow.link import InboundDataLink, OutBoundDataLink
from joop.dataflow.model import InboundFlowModel, PrimaryOutboundFlowModel


class DataFlow:
    """Coordinate one logical inbound/outbound flow family.

    A flow may support inbound links, outbound links, or both, but it must
    support at least one direction. For each supported direction there must be
    one primary data link type, and outbound flows may have additional
    secondary link types.
    """

    primary_inbound_data_link_type: type[InboundDataLink] | None = None
    primary_outbound_data_link_type: type[OutBoundDataLink] | None = None

    secondary_outbound_data_link_types: tuple[type[OutBoundDataLink], ...] = ()

    primary_inbound_data_link: InboundDataLink | None
    primary_outbound_data_link: OutBoundDataLink | None
    secondary_outbound_data_links: list[OutBoundDataLink]

    def __init__(self, create_missing: bool = False):
        self._check_if_implemented()

        self.primary_inbound_data_link = self._setup_inbound_link(
            self.primary_inbound_data_link_type,
            create_missing=create_missing,
        )
        self.primary_outbound_data_link = self._setup_outbound_link(
            self.primary_outbound_data_link_type,
            create_missing=create_missing,
        )
        self.secondary_outbound_data_links = [
            self._setup_outbound_link(
                data_link_type,
                create_missing=create_missing,
            )
            for data_link_type in self.secondary_outbound_data_link_types
        ]

    def _check_if_implemented(self) -> None:
        """Validate that this flow supports at least one complete direction."""
        supports_inbound = self.primary_inbound_data_link_type is not None
        supports_outbound = self.primary_outbound_data_link_type is not None

        if not supports_inbound and not supports_outbound:
            raise NotImplementedError(
                "DataFlow requires at least one primary inbound or outbound data link type."
            )

        if (not supports_outbound and
                len(self.secondary_outbound_data_link_types) > 0):
            raise NotImplementedError(
                "DataFlow requires a primary outbound data link type before adding "
                "secondary outbound data link types."
            )

    def _setup_inbound_link(
            self,
            data_link_type: type[InboundDataLink] | None,
            create_missing: bool = False,
            ) -> Optional[InboundDataLink]:
        """Instantiate an inbound link when one is configured."""
        if data_link_type is None:
            return None
        return data_link_type(create_missing=create_missing)

    def _setup_outbound_link(
            self,
            data_link_type: type[OutBoundDataLink] | None,
            create_missing: bool = False,
            ) -> Optional[OutBoundDataLink]:
        """Instantiate an outbound link when one is configured."""
        if data_link_type is None:
            return None
        return data_link_type(create_missing=create_missing)

    # outbound methods
    # ####

    def _queue_all(self, outbound_data: PrimaryOutboundFlowModel):
        """Queue outbound data on the primary and all secondaries."""
        if self.primary_outbound_data_link is None:
            raise RuntimeError("This DataFlow does not support outbound links.")

        self.primary_outbound_data_link.queue(outbound_data)
        for secondary in self.secondary_outbound_data_links:
            secondary.queue(outbound_data)

    def queue(self, outbound_data: PrimaryOutboundFlowModel):
        self._queue_all(outbound_data)

    def _publish(self, outbound_data: PrimaryOutboundFlowModel):
        """Publish on the primary outbound link only.

        Secondary outbound fan-out is intentionally left for later work.
        """
        if self.primary_outbound_data_link is None:
            raise RuntimeError("This DataFlow does not support outbound links.")
        return self.primary_outbound_data_link.publish(outbound_data)

    def _fetch(self) -> bool:
        """Fetch from the primary inbound link only."""
        if self.primary_inbound_data_link is None:
            raise RuntimeError("This DataFlow does not support inbound links.")
        return self.primary_inbound_data_link.fetch()

    def fetch(self) -> bool:
        return self._fetch()

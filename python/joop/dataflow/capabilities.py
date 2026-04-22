"""Capability objects for dataflow catchers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    """Describes what payload shapes a DataCatcher supports."""

    supports_related_models: bool = False

    @property
    def supports_json_backup(self) -> bool:
        """Whether JSON backup storage is viable for this catcher."""
        return self.supports_related_models

"""HTTP/REST-backed data catcher abstractions for joop.dataflow."""

import json
from urllib.parse import urlsplit
from typing import Iterator, Optional

import requests

from joop.dataflow.catchers import DataCatcher
from joop.dataflow.model import FlowModel


class RESTDataCatcher(DataCatcher):
    """Base class for HTTP/REST-backed catchers.

    REST catchers do not bind models onto an ORM base. They register the flow
    model type directly and leave transport-specific behavior to subclasses.
    """

    caching: bool = False
    round_trip: bool = False
    url: str | None = None

    @classmethod
    def _get_url(cls) -> str:
        """Return the single endpoint URL configured for this REST catcher."""
        url = getattr(cls, "url", None)
        if url is None or url == "":
            raise RuntimeError(
                f"{cls.__name__} requires a non-empty url to be configured."
            )
        return url

    @classmethod
    def _build_payload(cls, model: FlowModel) -> dict:
        """Build the default JSON payload for this REST catcher."""
        return model.model_dump(mode="json")

    @classmethod
    def _build_headers(cls, expect_reply: bool = False) -> dict[str, str]:
        """Build default headers for REST POST requests."""
        headers = {"Content-Type": "application/json"}
        if expect_reply:
            headers["Accept"] = "application/json"
        return headers

    @classmethod
    def _get_request_target(cls, client=None) -> str:
        """Return the request target for the supplied client."""
        target = cls._get_url()
        if client is None:
            return target

        parsed_target = urlsplit(target)
        if ((parsed_target.scheme != "" or parsed_target.netloc != "") and
                hasattr(client, "application")):
            return parsed_target.path or "/"
        return target

    @classmethod
    def _perform_request(
            cls,
            payload: dict,
            headers: dict[str, str],
            client=None,
            ):
        """POST the payload to the configured REST endpoint."""
        if client is None:
            client = requests.Session()
        return client.post(
            cls._get_request_target(client=client),
            json=payload,
            headers=headers,
        )

    @classmethod
    def _raise_for_status(cls, response) -> None:
        """Raise for transport-level errors on the response object."""
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
            return
        if getattr(response, "status_code", 200) >= 400:
            raise RuntimeError(
                f"{cls.__name__} request failed with status "
                f"{getattr(response, 'status_code', 'unknown')}."
            )

    @classmethod
    def _get_response_text(cls, response) -> str:
        """Extract response text from the transport response object."""
        if hasattr(response, "text"):
            return response.text.strip()
        return response.get_data(as_text=True).strip()

    @classmethod
    def _post_model(
            cls,
            model: FlowModel,
            expect_reply: bool = False,
            client=None,
            ) -> str:
        """POST the given model to the configured REST endpoint."""
        payload = cls._build_payload(model)
        headers = cls._build_headers(expect_reply=expect_reply)
        response = cls._perform_request(
            payload=payload,
            headers=headers,
            client=client,
        )
        cls._raise_for_status(response)
        return cls._get_response_text(response)

    @classmethod
    def _parse_send_response(cls, response_body: str, model: FlowModel):
        """Parse the response body for a one-way send."""
        if response_body == "":
            return model
        return cls.primary_model_type.model_validate(json.loads(response_body))

    @classmethod
    def _parse_exchange_response(
            cls,
            response_body: str,
            inbound_model_type: type[FlowModel],
            ):
        """Parse the response body for a round-trip exchange."""
        if response_body == "":
            return None
        return inbound_model_type.model_validate(json.loads(response_body))

    @classmethod
    def get_base_model(cls):
        """Return the registered model type for compatibility with catcher APIs."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        if primary_model_type is None:
            raise RuntimeError("Primary model must be registered before use.")
        return primary_model_type

    @classmethod
    def _get_registered_model_types(cls) -> tuple[type[FlowModel], ...]:
        """Return the registered primary model type."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        if primary_model_type is None:
            raise RuntimeError("Primary model must be registered before use.")

        return (primary_model_type,)

    @classmethod
    def set_primary_model(
            cls,
            primary_flow_model: type[FlowModel],
            **kwargs,
            ) -> None:
        """Register the flow model directly for this REST catcher."""
        primary_model_type = getattr(cls, "primary_model_type", None)
        abstract_model_type = getattr(cls, "abstract_model_type", None)
        if primary_model_type is not None:
            if primary_flow_model in (primary_model_type, abstract_model_type):
                return
            raise RuntimeError("Primary model already registered on this catcher.")

        cls.abstract_model_type = primary_flow_model
        cls.primary_model_type = primary_flow_model

    @classmethod
    def get_number_of_primary_records(cls) -> int:
        """REST catchers do not maintain a local primary record store."""
        cls._get_registered_model_types()
        return 0

    def __init__(self, *args, **kwargs):
        """REST catchers require only endpoint configuration by default."""
        self._get_url()
        return None

    @classmethod
    def send_model(cls, model: FlowModel, client=None):
        """Transmit a model through the configured REST endpoint via JSON POST."""
        cls._get_registered_model_types()
        cls._get_url()
        if not isinstance(model, cls.primary_model_type):
            raise TypeError(
                "RESTDataCatcher.send_model only accepts the registered "
                "primary model type."
            )

        response_body = cls._post_model(
            model,
            expect_reply=False,
            client=client,
        )
        return cls._parse_send_response(response_body, model)

    @classmethod
    def cache_model(cls, model: FlowModel):
        """REST catchers do not provide local cache storage."""
        cls._assert_caching_enabled()
        cls._get_registered_model_types()
        if not isinstance(model, cls.primary_model_type):
            raise TypeError(
                "RESTDataCatcher.cache_model only accepts the registered "
                "primary model type."
            )
        raise AssertionError(
            f"{cls.__name__} does not support local caching."
        )

    @classmethod
    def get_latest_model(cls) -> Optional[FlowModel]:
        """Fetch the latest model from the configured REST endpoint.

        Concrete REST catchers are expected to override this method.
        """
        cls._get_registered_model_types()
        cls._get_url()
        raise NotImplementedError(
            f"{cls.__name__}.get_latest_model must be implemented by RESTDataCatcher subclasses."
        )

    @classmethod
    def exchange_model(
            cls,
            outbound_model: FlowModel,
            inbound_model_type: type[FlowModel],
            client=None,
            ):
        """Exchange a model with the configured REST endpoint via JSON POST."""
        cls._get_registered_model_types()
        cls._get_url()
        if not isinstance(outbound_model, cls.primary_model_type):
            raise TypeError(
                "RESTDataCatcher.exchange_model only accepts the registered "
                "primary model type."
            )

        response_body = cls._post_model(
            outbound_model,
            expect_reply=True,
            client=client,
        )
        return cls._parse_exchange_response(response_body, inbound_model_type)

    @classmethod
    def iter_queued_models(cls) -> Iterator[FlowModel]:
        """REST catchers do not maintain a local replay queue."""
        cls._get_registered_model_types()
        return iter(())

    @classmethod
    def remove_queued_model(cls, model: FlowModel) -> bool:
        """REST catchers do not maintain a local replay queue."""
        cls._get_registered_model_types()
        return False

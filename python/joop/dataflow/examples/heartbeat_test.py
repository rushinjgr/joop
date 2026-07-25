"""An example heartbeat flow using local SQLite storage and a REST catcher.

This mirrors the style of ``sqlite_test.py``: define models, catchers, links,
and then exercise them directly. The remote heartbeat endpoint is simulated
with a small Flask app and a JSONComponent-backed response.
"""

import json

from flask import Flask, Response, request
from sqlmodel import Field

from joop.dataflow.flows.heartbeat import Heartbeat
from joop.dataflow.http import RESTDataCatcher
from joop.dataflow.link import OutBoundDataLink
from joop.dataflow.model import InboundFlowModel, OutboundUUIDModel
from joop.dataflow.sqlite import CachingSQLiteDataCatcher, SQLiteQueueDataCatcher
from joop.sql.sqlite import SQLiteDB
from joop.web import JSONComponent

##########################
# Define DB configs
inbound_sqlite_config = SQLiteDB.from_path("heartbeat_inbound.db")
outbound_sqlite_config = SQLiteDB.from_path("heartbeat_outbound.db")
##########################

##########################
# Define the heartbeat models.
class _HeartbeatModel(OutboundUUIDModel, table=False):
    message: str = "ping"


class _HeartbeatResponseModel(InboundFlowModel, table=False):
    id: int | None = Field(default=None, primary_key=True)
    message: str = "Reply to ping"
    received_message: str = "ping"
##########################

##########################
# Define the response component that will back the REST endpoint.
class HeartbeatResponseComponent(JSONComponent):

    class Inputs(JSONComponent.Inputs):
        received_message: str

    class Data(JSONComponent.Data):
        message: str
        received_message: str

        @classmethod
        def from_inputs(
                cls,
                inputs: "HeartbeatResponseComponent.Inputs",
                ) -> "HeartbeatResponseComponent.Data":
            return cls(
                message=f"Reply to {inputs.received_message}",
                received_message=inputs.received_message,
            )

    class SubComponents(JSONComponent.SubComponents):
        pass
##########################

##########################
# Build a tiny local Flask app to act as the remote heartbeat endpoint.
app = Flask(__name__)

# TODO replace with joop Flask facilities and routing

@app.post("/heartbeat")
def heartbeat_endpoint():
    payload = request.get_json(force=True) or {}

    response_component = HeartbeatResponseComponent()
    response_component.inputs = response_component.Inputs(
        received_message=payload.get("message", ""),
    )
    response_component.subs = response_component.SubComponents()

    if payload.get("queued_at") is not None:
        return ("", 204)

    rendered_data = json.loads(response_component.render())["data"]
    return Response(
        json.dumps(rendered_data),
        mimetype="application/json",
    )
##########################

##########################
# Create DataCatchers to control local state.
class LocalInboundDataCatcher(CachingSQLiteDataCatcher):
    sql_config = inbound_sqlite_config


class LocalOutboundDataCatcher(SQLiteQueueDataCatcher):
    sql_config = outbound_sqlite_config


class MyHeartbeatRESTDataCatcher(RESTDataCatcher):
    round_trip = True
    url = "/heartbeat"

    @classmethod
    def send_model(cls, model):
        return super().send_model(
            model,
            client=app.test_client(),
        )

    @classmethod
    def exchange_model(cls, outbound_model, inbound_model_type):
        return super().exchange_model(
            outbound_model,
            inbound_model_type=inbound_model_type,
            client=app.test_client(),
        )
##########################

##########################
# Create the data links. A heartbeat is bidirectional
#   but we just use an outbound. Internally, an artificial
#       inbound is created.

class MyOutboundDataLink(OutBoundDataLink):
    datamodel = _HeartbeatModel
    local_type = LocalOutboundDataCatcher
    remote_type = MyHeartbeatRESTDataCatcher
##########################

##########################
# Create the heartbeat flow itself.
class MyHeartbeat(Heartbeat):
    primary_outbound_data_link_type = MyOutboundDataLink
    remote_type = _HeartbeatResponseModel


my_heartbeat = MyHeartbeat(create_missing=True)
##########################

##########################
# Queue one earlier heartbeat, then send a new one and capture the reply.
queued_heartbeat = _HeartbeatModel(message="Earlier ping")
current_heartbeat = _HeartbeatModel(message="Current ping")

my_heartbeat.primary_outbound_data_link.queue(queued_heartbeat)
heartbeat_response = my_heartbeat.sync(current_heartbeat)
##########################

# `heartbeat_response` now holds the parsed inbound response model,
# and the response has also been stored in `heartbeat_inbound.db`.

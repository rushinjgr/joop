import unittest
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from sqlmodel import Field, Session, select

from joop.dataflow import SQLiteCacheDataCatcher
from joop.dataflow.flows.heartbeat import Heartbeat
from joop.dataflow.http import RESTDataCatcher
from joop.dataflow.link import (
    ArtificialDataLink,
    DataLink,
    InboundDataLink,
    OutBoundDataLink,
)
from joop.dataflow.model import (
    InboundFlowModel,
    OutboundCacheReason,
    OutboundUUIDFlowModelCache,
    OutboundUUIDModel,
)
from joop.dataflow.sqlite import BasicSQLiteDataCatcher
from joop.sql.sqlite import SQLiteDB


class TestDataflowModelRegistration(unittest.TestCase):
    def _build_registered_catcher(self, db_path: str):
        sqlite_config = SQLiteDB.from_path(db_path)

        class MyDataCatcher(SQLiteCacheDataCatcher):
            sql_config = sqlite_config

        base_model = MyDataCatcher.get_base_model()

        class MyUUIDModel(base_model, OutboundUUIDModel, table=True):
            message: str = "Hello."

        MyDataCatcher.set_primary_model(MyUUIDModel)
        MyDataCatcher(create_missing=True)
        return sqlite_config, MyDataCatcher, MyUUIDModel

    def test_primary_model_registration_binds_concrete_cache_model(self):
        with TemporaryDirectory() as temp_dir:
            _, MyDataCatcher, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "registration.sqlite")
            )

            cache_model = MyUUIDModel.get_cache_model()

            self.assertIs(MyDataCatcher.primary_model_type, MyUUIDModel)
            self.assertIs(MyDataCatcher.cache_model_type, cache_model)
            self.assertIsNot(cache_model, OutboundUUIDFlowModelCache)
            self.assertEqual(cache_model.__tablename__, "mydatacatchermyuuidmodel_cache")

    def test_shared_config_reuses_primary_model_and_isolates_cache_models(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "shared.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            MyDataCatcher.set_primary_model(_MyUUIDModel)
            MyOtherDataCatcher.set_primary_model(_MyUUIDModel)

            self.assertIs(
                MyDataCatcher.primary_model_type,
                MyOtherDataCatcher.primary_model_type,
            )
            self.assertEqual(MyDataCatcher.primary_model_type.__name__, "MyUUIDModel")
            self.assertEqual(MyDataCatcher.primary_model_type.__tablename__, "myuuidmodel")
            self.assertIsNot(
                MyDataCatcher.cache_model_type,
                MyOtherDataCatcher.cache_model_type,
            )
            self.assertEqual(
                MyDataCatcher.cache_model_type.__tablename__,
                "mydatacatchermyuuidmodel_cache",
            )
            self.assertEqual(
                MyOtherDataCatcher.cache_model_type.__tablename__,
                "myotherdatacatchermyuuidmodel_cache",
            )
            self.assertIs(
                _MyUUIDModel.get_cache_model(MyDataCatcher),
                MyDataCatcher.cache_model_type,
            )
            self.assertIs(
                _MyUUIDModel.get_cache_model(MyOtherDataCatcher),
                MyOtherDataCatcher.cache_model_type,
            )
            with self.assertRaises(RuntimeError):
                MyDataCatcher.primary_model_type.get_cache_model()

    def test_concrete_primary_model_is_reused_across_catchers_sharing_config(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "concrete.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            base_model = MyDataCatcher.get_base_model()

            class MyUUIDModel(base_model, OutboundUUIDModel, table=True):
                message: str = "Hello."

            MyDataCatcher.set_primary_model(MyUUIDModel)
            MyOtherDataCatcher.set_primary_model(MyUUIDModel)

            self.assertIs(MyDataCatcher.primary_model_type, MyUUIDModel)
            self.assertIs(MyOtherDataCatcher.primary_model_type, MyUUIDModel)
            self.assertEqual(MyUUIDModel.__tablename__, "myuuidmodel")

    def test_model_layer_naming_hooks_drive_generated_model_names(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "named.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class _NamedUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

                @classmethod
                def get_primary_model_name(cls):
                    return "SharedNamed"

                @classmethod
                def get_primary_model_class_name(cls, namespace=None):
                    return "SharedNamedRecord"

                @classmethod
                def get_primary_model_table_name(cls):
                    return "shared_named_records"

                @classmethod
                def get_cache_model_name(cls, data_catcher_type=None):
                    if data_catcher_type is None:
                        return "SharedNamedBuffer"
                    return f"{data_catcher_type.__name__}SharedNamedBuffer"

                @classmethod
                def get_cache_model_class_name(
                        cls,
                        data_catcher_type=None,
                        namespace=None,
                        ):
                    prefix = ""
                    if namespace is not None and namespace != "":
                        prefix = f"{namespace}_"
                    return (
                        f"{prefix}{cls.get_cache_model_name(data_catcher_type=data_catcher_type)}"
                        "Store"
                    )

                @classmethod
                def get_cache_model_table_name(cls, data_catcher_type=None):
                    cache_name = cls.get_cache_model_name(data_catcher_type=data_catcher_type)
                    return f"{cache_name.lower()}_buffer"

            MyDataCatcher.set_primary_model(_NamedUUIDModel)

            self.assertEqual(
                MyDataCatcher.primary_model_type.__name__,
                "SharedNamedRecord",
            )
            self.assertEqual(
                MyDataCatcher.primary_model_type.__tablename__,
                "shared_named_records",
            )
            self.assertEqual(
                MyDataCatcher.cache_model_type.__name__,
                "sqlite_MyDataCatcherSharedNamedBufferStore",
            )
            self.assertEqual(
                MyDataCatcher.cache_model_type.__tablename__,
                "mydatacatchersharednamedbuffer_buffer",
            )

    def test_api_data_catcher_registers_primary_model_directly(self):
        class MyRESTDataCatcher(RESTDataCatcher):
            pass

        class _MyUUIDModel(OutboundUUIDModel, table=False):
            message: str = "Hello."

        MyRESTDataCatcher.set_primary_model(_MyUUIDModel)

        self.assertIs(MyRESTDataCatcher.abstract_model_type, _MyUUIDModel)
        self.assertIs(MyRESTDataCatcher.primary_model_type, _MyUUIDModel)
        self.assertEqual(
            MyRESTDataCatcher._get_registered_model_types(),
            (_MyUUIDModel,),
        )

    def test_rest_data_catcher_send_model_posts_json_to_url(self):
        class MyRESTDataCatcher(RESTDataCatcher):
            url = "http://localhost/test"

        class _MyUUIDModel(OutboundUUIDModel, table=False):
            message: str = "Hello."

        class FakeResponse:
            text = ""

            def raise_for_status(self):
                return None

        class FakeClient:
            def post(self, url, json=None, headers=None):
                self.url = url
                self.json = json
                self.headers = headers
                return FakeResponse()

        MyRESTDataCatcher.set_primary_model(_MyUUIDModel)
        model = _MyUUIDModel(message="Posted")

        fake_client = FakeClient()
        returned_model = MyRESTDataCatcher.send_model(model, client=fake_client)

        self.assertEqual(fake_client.url, "http://localhost/test")
        self.assertEqual(fake_client.headers["Content-Type"], "application/json")
        self.assertEqual(fake_client.json["message"], "Posted")
        self.assertEqual(returned_model.message, "Posted")

    def test_rest_data_catcher_exchange_model_parses_json_response(self):
        class MyRESTDataCatcher(RESTDataCatcher):
            round_trip = True
            url = "http://localhost/heartbeat"

        class _MyUUIDModel(OutboundUUIDModel, table=False):
            message: str = "Hello."

        class _MyInboundModel(InboundFlowModel, table=False):
            id: int | None = Field(default=None, primary_key=True)
            message: str = "Hello."

        class FakeResponse:
            text = json.dumps({"message": "Reply to Ping"})

            def raise_for_status(self):
                return None

        class FakeClient:
            def post(self, url, json=None, headers=None):
                self.url = url
                self.json = json
                self.headers = headers
                return FakeResponse()

        MyRESTDataCatcher.set_primary_model(_MyUUIDModel)
        model = _MyUUIDModel(message="Ping")

        fake_client = FakeClient()
        response_model = MyRESTDataCatcher.exchange_model(
            model,
            inbound_model_type=_MyInboundModel,
            client=fake_client,
        )

        self.assertEqual(fake_client.url, "http://localhost/heartbeat")
        self.assertEqual(fake_client.headers["Content-Type"], "application/json")
        self.assertEqual(fake_client.headers["Accept"], "application/json")
        self.assertEqual(fake_client.json["message"], "Ping")
        self.assertIsNotNone(response_model)
        self.assertEqual(response_model.message, "Reply to Ping")

    def test_send_model_persists_registered_primary_model(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config, MyDataCatcher, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "primary.sqlite")
            )

            MyDataCatcher.send_model(MyUUIDModel(message="Saved"))

            with Session(sqlite_config.get_engine()) as session:
                rows = list(session.exec(select(MyUUIDModel)).all())

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].message, "Saved")

    def test_get_number_of_cached_records_counts_registered_cache_rows(self):
        with TemporaryDirectory() as temp_dir:
            _, MyDataCatcher, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "cache.sqlite")
            )

            cache_model = MyUUIDModel.get_cache_model()
            MyDataCatcher.send_model(cache_model())
            MyDataCatcher.send_model(cache_model())

            self.assertEqual(MyDataCatcher.get_number_of_cached_records(), 2)

    def test_cache_model_marks_primary_row_as_cached(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config, MyDataCatcher, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "primary_cached.sqlite")
            )

            MyDataCatcher.cache_model(MyUUIDModel(message="Buffered"))

            with Session(sqlite_config.get_engine()) as session:
                primary_rows = list(session.exec(select(MyUUIDModel)).all())

            self.assertEqual(len(primary_rows), 1)
            self.assertIsNotNone(primary_rows[0].cached_at)

    def test_primary_and_cached_record_counts_are_tracked_separately(self):
        with TemporaryDirectory() as temp_dir:
            _, MyDataCatcher, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "counts.sqlite")
            )

            MyDataCatcher.send_model(MyUUIDModel(message="First"))
            MyDataCatcher.send_model(MyUUIDModel(message="Second"))

            cache_model = MyUUIDModel.get_cache_model()
            MyDataCatcher.send_model(cache_model())

            self.assertEqual(MyDataCatcher.get_number_of_primary_records(), 2)
            self.assertEqual(MyDataCatcher.get_number_of_cached_records(), 1)

    def test_cache_model_defaults_to_timezone_aware_timestamp(self):
        with TemporaryDirectory() as temp_dir:
            _, _, MyUUIDModel = self._build_registered_catcher(
                str(Path(temp_dir) / "timestamp.sqlite")
            )

            cache_instance = MyUUIDModel.get_cache_model()()

            self.assertIsNotNone(cache_instance.cached_at)
            self.assertIsNotNone(cache_instance.cached_at.tzinfo)

    def test_send_model_accepts_bound_abstract_model(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "abstract_send.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            MyDataCatcher.set_primary_model(_MyUUIDModel)
            MyDataCatcher(create_missing=True)
            MyDataCatcher.send_model(_MyUUIDModel(message="Abstract Save"))

            with Session(sqlite_config.get_engine()) as session:
                rows = list(session.exec(select(MyDataCatcher.primary_model_type)).all())

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].message, "Abstract Save")

    def test_datalink_registers_catcher_specific_model_types(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=MyOtherDataCatcher,
                create_missing=True,
            )

            self.assertIsInstance(datalink.local, MyDataCatcher)
            self.assertIsInstance(datalink.remote, MyOtherDataCatcher)
            self.assertIs(MyDataCatcher.abstract_model_type, _MyUUIDModel)
            self.assertIs(MyOtherDataCatcher.abstract_model_type, _MyUUIDModel)
            self.assertIsNot(
                MyDataCatcher.primary_model_type,
                MyOtherDataCatcher.primary_model_type,
            )
            self.assertEqual(MyDataCatcher.primary_model_type.__tablename__, "myuuidmodel")
            self.assertEqual(
                MyOtherDataCatcher.primary_model_type.__tablename__,
                "myuuidmodel",
            )
            self.assertTrue(issubclass(MyDataCatcher.primary_model_type, _MyUUIDModel))
            self.assertTrue(
                issubclass(MyOtherDataCatcher.primary_model_type, _MyUUIDModel)
            )

    def test_ambiguous_registry_candidates_raise_clear_error(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "ambiguous.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class FirstCandidate(_MyUUIDModel, table=False):
                pass

            class SecondCandidate(_MyUUIDModel, table=False):
                pass

            with patch.object(
                    MyDataCatcher,
                    "_get_compatible_primary_model_types",
                    return_value=(FirstCandidate, SecondCandidate),
                    ):
                with self.assertRaisesRegex(
                        RuntimeError,
                        "Multiple registered primary models match",
                        ):
                    MyDataCatcher.set_primary_model(_MyUUIDModel)

    def test_datalink_publish_stores_to_remote_on_success(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=MyOtherDataCatcher,
                create_missing=True,
            )

            datalink.publish(_MyUUIDModel(message="Published"))

            with Session(other_sqlite_config.get_engine()) as session:
                remote_rows = list(
                    session.exec(select(MyOtherDataCatcher.primary_model_type)).all()
                )
            with Session(sqlite_config.get_engine()) as session:
                local_rows = list(
                    session.exec(select(MyDataCatcher.primary_model_type)).all()
                )

            self.assertEqual(len(remote_rows), 1)
            self.assertEqual(remote_rows[0].message, "Published")
            self.assertEqual(local_rows, [])

    def test_datalink_get_latest_local_returns_most_recent_primary_row(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=MyOtherDataCatcher,
                create_missing=True,
            )

            earlier = _MyUUIDModel(
                message="Earlier",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            later = _MyUUIDModel(
                message="Later",
                created_at=datetime.now(timezone.utc),
            )

            MyDataCatcher.send_model(earlier)
            MyDataCatcher.send_model(later)

            latest_local = datalink.get_latest_local()

            self.assertIsNotNone(latest_local)
            self.assertEqual(latest_local.id, later.id)
            self.assertEqual(latest_local.message, "Later")

    def test_datalink_get_latest_local_returns_none_when_empty(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=MyOtherDataCatcher,
                create_missing=True,
            )

            self.assertIsNone(datalink.get_latest_local())

    def test_inbound_datalink_fetch_prefers_remote_and_returns_unviewed_status(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class RemoteInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = other_sqlite_config

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = InboundDataLink(
                datamodel=_MyInboundModel,
                local_type=LocalInboundDataCatcher,
                remote_type=RemoteInboundDataCatcher,
                create_missing=True,
            )

            remote_model = _MyInboundModel(message="Remote")
            local_model = _MyInboundModel(
                message="Local",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
                last_viewed=datetime.now(timezone.utc) - timedelta(minutes=30),
            )

            RemoteInboundDataCatcher.send_model(remote_model)
            LocalInboundDataCatcher.send_model(local_model)

            never_viewed = datalink.fetch()

            self.assertTrue(never_viewed)
            self.assertIsNotNone(datalink.current_model)
            self.assertEqual(datalink.current_model.message, "Remote")

    def test_inbound_datalink_fetch_falls_back_to_latest_local_on_remote_failure(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class RemoteInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = other_sqlite_config

                @classmethod
                def get_latest_model(cls):
                    raise RuntimeError("remote unavailable")

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = InboundDataLink(
                datamodel=_MyInboundModel,
                local_type=LocalInboundDataCatcher,
                remote_type=RemoteInboundDataCatcher,
                create_missing=True,
            )

            local_model = _MyInboundModel(
                message="Local",
                last_viewed=datetime.now(timezone.utc) - timedelta(minutes=15),
            )
            LocalInboundDataCatcher.send_model(local_model)

            never_viewed = datalink.fetch()

            self.assertFalse(never_viewed)
            self.assertIsNotNone(datalink.current_model)
            self.assertEqual(datalink.current_model.message, "Local")

    def test_inbound_datalink_fetch_returns_false_when_no_model_exists(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class RemoteInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = other_sqlite_config

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = InboundDataLink(
                datamodel=_MyInboundModel,
                local_type=LocalInboundDataCatcher,
                remote_type=RemoteInboundDataCatcher,
                create_missing=True,
            )

            self.assertFalse(datalink.fetch())
            self.assertIsNone(datalink.current_model)

    def test_inbound_datalink_accept_persists_model_locally(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class RemoteInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = other_sqlite_config

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = InboundDataLink(
                datamodel=_MyInboundModel,
                local_type=LocalInboundDataCatcher,
                remote_type=RemoteInboundDataCatcher,
                create_missing=True,
            )

            stored_model = datalink.accept(_MyInboundModel(message="Returned"))

            with Session(sqlite_config.get_engine()) as session:
                local_rows = list(
                    session.exec(select(LocalInboundDataCatcher.primary_model_type)).all()
                )

            self.assertEqual(len(local_rows), 1)
            self.assertEqual(local_rows[0].message, "Returned")
            self.assertEqual(stored_model.message, "Returned")
            self.assertIsNotNone(datalink.current_model)
            self.assertEqual(datalink.current_model.message, "Returned")

    def test_inbound_datalink_requires_non_caching_local_catcher(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalInboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = other_sqlite_config

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            with self.assertRaisesRegex(
                    TypeError,
                    "InboundDataLink requires a non-caching local_type",
                    ):
                InboundDataLink(
                    datamodel=_MyInboundModel,
                    local_type=LocalInboundDataCatcher,
                    remote_type=RemoteInboundDataCatcher,
                    create_missing=True,
                )

    def test_artificial_datalink_works_without_remote_type(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            class MyArtificialDataLink(ArtificialDataLink):
                datamodel = _MyInboundModel
                local_type = LocalInboundDataCatcher

            datalink = MyArtificialDataLink(create_missing=True)
            datalink.accept(_MyInboundModel(message="Accepted"))

            self.assertTrue(datalink.fetch())
            self.assertIsNotNone(datalink.current_model)
            self.assertEqual(datalink.current_model.message, "Accepted")

    def test_outbound_datalink_requires_caching_local_catcher(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            with self.assertRaisesRegex(
                    TypeError,
                    "OutBoundDataLink requires a caching local_type",
                    ):
                OutBoundDataLink(
                    datamodel=_MyUUIDModel,
                    local_type=LocalOutboundDataCatcher,
                    remote_type=RemoteOutboundDataCatcher,
                    create_missing=True,
                )

    def test_outbound_datalink_get_queue_length_counts_local_cache_rows(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            LocalOutboundDataCatcher.send_model(_MyUUIDModel(message="Primary Only"))
            LocalOutboundDataCatcher.cache_model(_MyUUIDModel(message="Buffered"))
            LocalOutboundDataCatcher.cache_model(_MyUUIDModel(message="Buffered Again"))

            self.assertEqual(
                LocalOutboundDataCatcher.get_number_of_primary_records(),
                3,
            )
            self.assertEqual(datalink.get_queue_length(), 2)

    def test_outbound_datalink_exchange_returns_response_model(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config
                round_trip = True

                @classmethod
                def exchange_model(cls, outbound_model, inbound_model_type):
                    return inbound_model_type(message=f"Reply to {outbound_model.message}")

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            response_model = datalink.exchange(
                _MyUUIDModel(message="Ping"),
                inbound_model_type=_MyInboundModel,
            )

            self.assertIsNotNone(response_model)
            self.assertEqual(response_model.message, "Reply to Ping")
            self.assertEqual(LocalOutboundDataCatcher.get_number_of_cached_records(), 0)

    def test_outbound_datalink_exchange_supports_api_remote_catcher(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(RESTDataCatcher):
                round_trip = True
                url = "http://localhost/heartbeat"

                @classmethod
                def exchange_model(cls, outbound_model, inbound_model_type):
                    return inbound_model_type(message=f"Reply to {outbound_model.message}")

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            response_model = datalink.exchange(
                _MyUUIDModel(message="Ping"),
                inbound_model_type=_MyInboundModel,
            )

            self.assertIsNotNone(response_model)
            self.assertEqual(response_model.message, "Reply to Ping")

    def test_outbound_datalink_exchange_requires_round_trip_remote_catcher(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            with self.assertRaisesRegex(
                    RuntimeError,
                    "OutBoundDataLink.exchange requires a round-trip remote_type",
                    ):
                datalink.exchange(
                    _MyUUIDModel(message="Ping"),
                    inbound_model_type=_MyInboundModel,
                )

    def test_outbound_datalink_exchange_queues_on_remote_failure(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config
                round_trip = True

                @classmethod
                def exchange_model(cls, outbound_model, inbound_model_type):
                    raise RuntimeError("remote unavailable")

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class _MyInboundModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            response_model = datalink.exchange(
                _MyUUIDModel(message="Ping"),
                inbound_model_type=_MyInboundModel,
            )

            with Session(sqlite_config.get_engine()) as session:
                local_rows = list(
                    session.exec(select(LocalOutboundDataCatcher.primary_model_type)).all()
                )
                local_cache_rows = list(
                    session.exec(select(LocalOutboundDataCatcher.cache_model_type)).all()
                )

            self.assertIsNone(response_model)
            self.assertEqual(len(local_rows), 1)
            self.assertEqual(local_rows[0].message, "Ping")
            self.assertEqual(len(local_cache_rows), 1)
            self.assertEqual(local_cache_rows[0].cache_reason, OutboundCacheReason.FAIL)

    def test_outbound_datalink_sync_drains_queue_before_new_publish(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config
                sent_messages = []

                @classmethod
                def send_model(cls, model):
                    cls.sent_messages.append(model.message)
                    return super().send_model(model)

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            datalink.queue(_MyUUIDModel(message="Queued First"))
            datalink.queue(_MyUUIDModel(message="Queued Second"))
            datalink.sync(_MyUUIDModel(message="New Third"))

            with Session(other_sqlite_config.get_engine()) as session:
                remote_rows = list(
                    session.exec(select(RemoteOutboundDataCatcher.primary_model_type)).all()
                )

            self.assertEqual(
                RemoteOutboundDataCatcher.sent_messages,
                ["Queued First", "Queued Second", "New Third"],
            )
            self.assertEqual(LocalOutboundDataCatcher.get_number_of_cached_records(), 0)
            self.assertEqual(len(remote_rows), 3)

    def test_outbound_datalink_sync_stops_on_first_replay_failure(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config
                attempted_messages = []

                @classmethod
                def send_model(cls, model):
                    cls.attempted_messages.append(model.message)
                    if model.message == "Queued Second":
                        raise RuntimeError("remote unavailable")
                    return super().send_model(model)

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            first = datalink.queue(_MyUUIDModel(message="Queued First"))
            second = datalink.queue(_MyUUIDModel(message="Queued Second"))
            third = datalink.queue(_MyUUIDModel(message="Queued Third"))

            datalink.sync(None)

            with Session(sqlite_config.get_engine()) as session:
                remaining_cache_rows = list(
                    session.exec(select(LocalOutboundDataCatcher.cache_model_type)).all()
                )

            self.assertEqual(
                RemoteOutboundDataCatcher.attempted_messages,
                ["Queued First", "Queued Second"],
            )
            self.assertEqual(LocalOutboundDataCatcher.get_number_of_cached_records(), 2)
            self.assertEqual(
                {row.id for row in remaining_cache_rows},
                {second.id, third.id},
            )
            self.assertNotIn(first.id, {row.id for row in remaining_cache_rows})

    def test_outbound_datalink_sync_drops_orphaned_cache_rows(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = OutBoundDataLink(
                datamodel=_MyUUIDModel,
                local_type=LocalOutboundDataCatcher,
                remote_type=RemoteOutboundDataCatcher,
                create_missing=True,
            )

            LocalOutboundDataCatcher.send_model(
                LocalOutboundDataCatcher.cache_model_type(id=uuid4())
            )

            datalink.sync(None)

            self.assertEqual(LocalOutboundDataCatcher.get_number_of_cached_records(), 0)

    def test_heartbeat_requires_primary_inbound_and_outbound_links(self):
        class OutboundOnlyHeartbeat(Heartbeat):
            primary_outbound_data_link_type = OutBoundDataLink

        with self.assertRaisesRegex(
                NotImplementedError,
                "Heartbeat requires a primary inbound data link type.",
                ):
            OutboundOnlyHeartbeat()

    def test_heartbeat_sync_drains_backlog_and_persists_response(self):
        with TemporaryDirectory() as temp_dir:
            inbound_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "inbound.sqlite"))
            outbound_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "outbound.sqlite"))
            remote_outbound_sqlite_config = SQLiteDB.from_path(
                str(Path(temp_dir) / "remote_outbound.sqlite")
            )

            class LocalInboundDataCatcher(BasicSQLiteDataCatcher):
                sql_config = inbound_sqlite_config

            class LocalOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = outbound_sqlite_config

            class RemoteOutboundDataCatcher(SQLiteCacheDataCatcher):
                sql_config = remote_outbound_sqlite_config
                round_trip = True
                events = []

                @classmethod
                def send_model(cls, model):
                    cls.events.append(f"send:{model.message}")
                    return super().send_model(model)

                @classmethod
                def exchange_model(cls, outbound_model, inbound_model_type):
                    cls.events.append(f"exchange:{outbound_model.message}")
                    return inbound_model_type(message=f"Reply to {outbound_model.message}")

            class _HeartbeatModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            class _ResponseModel(InboundFlowModel, table=False):
                id: int | None = Field(default=None, primary_key=True)
                message: str = "Hello."

            class MyInboundDataLink(ArtificialDataLink):
                datamodel = _ResponseModel
                local_type = LocalInboundDataCatcher

            class MyOutboundDataLink(OutBoundDataLink):
                datamodel = _HeartbeatModel
                local_type = LocalOutboundDataCatcher
                remote_type = RemoteOutboundDataCatcher

            class MyHeartbeat(Heartbeat):
                primary_inbound_data_link_type = MyInboundDataLink
                primary_outbound_data_link_type = MyOutboundDataLink

            heartbeat = MyHeartbeat(create_missing=True)
            heartbeat.primary_outbound_data_link.queue(
                _HeartbeatModel(message="Queued First")
            )

            response_model = heartbeat.sync(_HeartbeatModel(message="Ping"))

            with Session(inbound_sqlite_config.get_engine()) as session:
                inbound_rows = list(
                    session.exec(select(LocalInboundDataCatcher.primary_model_type)).all()
                )

            self.assertEqual(
                RemoteOutboundDataCatcher.events,
                ["send:Queued First", "exchange:Ping"],
            )
            self.assertIsNotNone(response_model)
            self.assertEqual(response_model.message, "Reply to Ping")
            self.assertEqual(len(inbound_rows), 1)
            self.assertEqual(inbound_rows[0].message, "Reply to Ping")
            self.assertEqual(LocalOutboundDataCatcher.get_number_of_cached_records(), 0)

    def test_datalink_publish_falls_back_to_local_on_remote_failure(self):
        with TemporaryDirectory() as temp_dir:
            sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            other_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "remote.sqlite"))

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = sqlite_config

            class MyOtherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = other_sqlite_config

                @classmethod
                def send_model(cls, model):
                    raise RuntimeError("remote unavailable")

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            datalink = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=MyOtherDataCatcher,
                create_missing=True,
            )

            datapoint = _MyUUIDModel(message="Buffered")
            datalink.publish(datapoint)

            with Session(sqlite_config.get_engine()) as session:
                local_rows = list(
                    session.exec(select(MyDataCatcher.primary_model_type)).all()
                )
                local_cache_rows = list(
                    session.exec(select(MyDataCatcher.cache_model_type)).all()
                )

            self.assertEqual(len(local_rows), 1)
            self.assertEqual(local_rows[0].id, datapoint.id)
            self.assertEqual(local_rows[0].message, "Buffered")
            self.assertEqual(len(local_cache_rows), 1)
            self.assertEqual(local_cache_rows[0].id, datapoint.id)
            self.assertEqual(local_cache_rows[0].cache_reason, OutboundCacheReason.FAIL)
            self.assertIsNotNone(local_cache_rows[0].cached_at)

    def test_only_failing_link_caches_when_cache_catchers_share_one_sqlconfig(self):
        with TemporaryDirectory() as temp_dir:
            shared_sqlite_config = SQLiteDB.from_path(str(Path(temp_dir) / "local.sqlite"))
            first_remote_sqlite_config = SQLiteDB.from_path(
                str(Path(temp_dir) / "first_remote.sqlite")
            )
            second_remote_sqlite_config = SQLiteDB.from_path(
                str(Path(temp_dir) / "second_remote.sqlite")
            )

            class MyDataCatcher(SQLiteCacheDataCatcher):
                sql_config = shared_sqlite_config

            class AnotherDataCatcher(SQLiteCacheDataCatcher):
                sql_config = shared_sqlite_config

            class SuccessfulRemoteDataCatcher(SQLiteCacheDataCatcher):
                sql_config = first_remote_sqlite_config

            class FailingRemoteDataCatcher(SQLiteCacheDataCatcher):
                sql_config = second_remote_sqlite_config

                @classmethod
                def send_model(cls, model):
                    raise RuntimeError("remote unavailable")

            class _MyUUIDModel(OutboundUUIDModel, table=False):
                message: str = "Hello."

            successful_link = DataLink(
                datamodel=_MyUUIDModel,
                local_type=MyDataCatcher,
                remote_type=SuccessfulRemoteDataCatcher,
                create_missing=True,
            )
            failing_link = DataLink(
                datamodel=_MyUUIDModel,
                local_type=AnotherDataCatcher,
                remote_type=FailingRemoteDataCatcher,
                create_missing=True,
            )

            successful_datapoint = _MyUUIDModel(message="Published")
            failing_datapoint = _MyUUIDModel(message="Buffered")

            successful_link.publish(successful_datapoint)
            failing_link.publish(failing_datapoint)

            with Session(shared_sqlite_config.get_engine()) as session:
                local_primary_rows = list(
                    session.exec(select(MyDataCatcher.primary_model_type)).all()
                )
                first_cache_rows = list(
                    session.exec(select(MyDataCatcher.cache_model_type)).all()
                )
                second_cache_rows = list(
                    session.exec(select(AnotherDataCatcher.cache_model_type)).all()
                )
            with Session(first_remote_sqlite_config.get_engine()) as session:
                remote_rows = list(
                    session.exec(select(SuccessfulRemoteDataCatcher.primary_model_type)).all()
                )

            self.assertEqual(len(local_primary_rows), 1)
            self.assertEqual(local_primary_rows[0].id, failing_datapoint.id)
            self.assertEqual(local_primary_rows[0].message, "Buffered")
            self.assertEqual(first_cache_rows, [])
            self.assertEqual(len(second_cache_rows), 1)
            self.assertEqual(second_cache_rows[0].id, failing_datapoint.id)
            self.assertEqual(second_cache_rows[0].cache_reason, OutboundCacheReason.FAIL)
            self.assertEqual(len(remote_rows), 1)
            self.assertEqual(remote_rows[0].id, successful_datapoint.id)
            self.assertEqual(remote_rows[0].message, "Published")


if __name__ == "__main__":
    unittest.main()

import unittest
from ipaddress import IPv4Address
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlmodel import Field, Session, SQLModel, select
from sqlalchemy.exc import SQLAlchemyError

from joop.net import Credential
from joop.sql import ORMSQLConfig, SQLConfig, SQLScheme
from joop.sql.sqlite import SQLiteDB as RealSQLiteDB

class SQLiteDB(RealSQLiteDB):

    def clear_model_storage(self, model_type: type[SQLModel]) -> None:
        """Delete all rows for a SQLModel-backed table using this SQLite config."""
        engine = self.get_engine()
        self._registry.metadata.create_all(engine)
        with Session(engine) as session:
            rows = session.exec(select(model_type)).all()
            for row in rows:
                session.delete(row)
            session.commit()


class SQLiteStorageTestModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    message: str

class TestSQLConfig(unittest.TestCase):
    def test_sql_config_initialization(self):
        credential = Credential(username="user", password="pass")
        config = SQLConfig(
            scheme=SQLScheme.POSTGRESQL,
            driver=None,
            host="localhost",
            port=5432,
            credential=credential,
            schema_name="test_db",
        )
        self.assertEqual(config.scheme, SQLScheme.POSTGRESQL)
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.credential, credential)
        self.assertEqual(config.schema_name, "test_db")
        self.assertEqual(config.url, "postgresql://user:pass@localhost:5432/test_db")

    def test_sql_config_from_url_preserves_string_host(self):
        config = SQLConfig.from_url("postgresql://user:pass@127.0.0.1:5432/test_db")
        self.assertEqual(config.scheme, SQLScheme.POSTGRESQL)
        self.assertIsNone(config.driver)
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.credential, Credential(username="user", password="pass"))
        self.assertEqual(config.schema_name, "test_db")

    def test_sql_config_supports_driver_in_url(self):
        config = SQLConfig(
            scheme=SQLScheme.MSSQL,
            driver="pyodbc",
            host="localhost",
            port=1433,
            credential=Credential(username="sa", password="pass"),
            schema_name="master",
        )
        self.assertEqual(config.scheme, SQLScheme.MSSQL)
        self.assertEqual(config.driver, "pyodbc")
        self.assertEqual(config.url, "mssql+pyodbc://sa:pass@localhost:1433/master")

    def test_sql_config_from_url_parses_driver(self):
        config = SQLConfig.from_url("mssql+pyodbc://sa:pass@127.0.0.1:1433/master")
        self.assertEqual(config.scheme, SQLScheme.MSSQL)
        self.assertEqual(config.driver, "pyodbc")
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 1433)
        self.assertEqual(config.credential, Credential(username="sa", password="pass"))
        self.assertEqual(config.schema_name, "master")

    def test_sql_config_allows_custom_scheme_strings(self):
        config = SQLConfig(
            scheme="cockroachdb",
            driver=None,
            host="localhost",
            port=26257,
            credential=None,
            schema_name="defaultdb",
        )
        self.assertEqual(config.scheme, "cockroachdb")
        self.assertEqual(config.url, "cockroachdb://localhost:26257/defaultdb")

    def test_check_accessible_redacts_credentials_in_errors(self):
        credential = Credential(username="user", password="secret-pass")
        config = SQLConfig(
            scheme=SQLScheme.POSTGRESQL,
            driver=None,
            host="localhost",
            port=5432,
            credential=credential,
            schema_name="test_db",
        )

        class BrokenEngine:
            def connect(self):
                raise SQLAlchemyError("boom")

        config._engine = BrokenEngine()

        with self.assertRaises(RuntimeError) as raised:
            config.check_accessible()

        self.assertIn(config.redacted_url, str(raised.exception))
        self.assertNotIn("secret-pass", str(raised.exception))
        self.assertNotIn("user:secret-pass", str(raised.exception))

class TestSQLiteConfig(unittest.TestCase):
    def test_sqlite_config_accepts_typed_ip_host_without_rewriting(self):
        config = SQLiteDB(
            scheme=SQLScheme.SQLITE,
            driver=None,
            host=IPv4Address("127.0.0.1"),
            port=None,
            credential=None,
            schema_name="local.db",
        )
        self.assertEqual(config.host, IPv4Address("127.0.0.1"))

    def test_sqlite_config_from_url_returns_sqlite_config(self):
        config = SQLiteDB.from_url("sqlite:///:memory:")
        self.assertIsInstance(config, SQLiteDB)
        self.assertEqual(config.schema_name, ":memory:")

    def test_sqlite_config_returns_sqlalchemy_engine_url(self):
        config = SQLiteDB.from_path("local.db")
        self.assertEqual(config.get_engine_url(), "sqlite:///local.db")

    def test_sqlite_config_supports_in_memory_databases(self):
        config = SQLiteDB.from_path(":memory:")
        self.assertEqual(config.get_engine_url(), "sqlite:///:memory:")

    def test_get_engine_returns_cached_engine(self):
        config = SQLiteDB.from_path(":memory:")
        first_engine = config.get_engine()
        second_engine = config.get_engine()
        self.assertIs(first_engine, second_engine)

    def test_clear_model_storage_removes_existing_rows(self):
        with TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "clear_storage.sqlite")
            config = SQLiteDB.from_path(db_path)
            engine = config.get_engine()
            SQLModel.metadata.create_all(engine)

            with Session(engine) as session:
                session.add(SQLiteStorageTestModel(message="hello"))
                session.commit()

            config.clear_model_storage(SQLiteStorageTestModel)

            with Session(engine) as session:
                rows = list(session.exec(select(SQLiteStorageTestModel)).all())

            self.assertEqual(rows, [])

class TestORMSQLConfig(unittest.TestCase):
    def test_orm_sql_config_initialization(self):
        config = ORMSQLConfig(
            scheme=SQLScheme.POSTGRESQL,
            driver=None,
            host="localhost",
            port=5432,
            credential=Credential(username="user", password="pass"),
            schema_name="test_db",
        )
        self.assertEqual(config.scheme, SQLScheme.POSTGRESQL)
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.credential, Credential(username="user", password="pass"))
        self.assertEqual(config.schema_name, "test_db")

    def test_orm_base_model_does_not_force_scheme_as_table_schema(self):
        config = SQLiteDB.from_path(":memory:")
        base_model = config.basemodel

        class SQLiteScopedModel(base_model, table=True):
            id: int | None = Field(default=None, primary_key=True)

        self.assertIsNone(SQLiteScopedModel.__table__.schema)

if __name__ == "__main__":
    unittest.main()

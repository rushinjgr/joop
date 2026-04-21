import unittest
from ipaddress import IPv4Address

from joop.net import Credential
from joop.sql import SQLConfig, ORMSQLConfig, SQLScheme

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

    def test_sql_config_from_url_uses_stdlib_ip_type(self):
        config = SQLConfig.from_url("postgresql://user:pass@127.0.0.1:5432/test_db")
        self.assertEqual(config.scheme, SQLScheme.POSTGRESQL)
        self.assertIsNone(config.driver)
        self.assertEqual(config.host, IPv4Address("127.0.0.1"))
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
        self.assertEqual(config.host, IPv4Address("127.0.0.1"))
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

class TestORMSQLConfig(unittest.TestCase):
    def test_orm_sql_config_initialization(self):
        config = ORMSQLConfig(
            scheme=SQLScheme.POSTGRESQL,
            driver=None,
            host="localhost",
            port=5432,
            credential=Credential(username="user", password="pass"),
            schema_name="test_db",
            db_module_path="path.to.module",
        )
        self.assertEqual(config.scheme, SQLScheme.POSTGRESQL)
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.credential, Credential(username="user", password="pass"))
        self.assertEqual(config.schema_name, "test_db")
        self.assertEqual(config.db_module_path, "path.to.module")

if __name__ == "__main__":
    unittest.main()

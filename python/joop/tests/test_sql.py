import unittest
from joop.sql import SQLConfig, ORMSQLConfig

class TestSQLConfig(unittest.TestCase):
    def test_sql_config_initialization(self):
        config = SQLConfig(host="localhost", port=5432, username="user", password="pass", schema_name="test_db")
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.username, "user")
        self.assertEqual(config.password, "pass")
        self.assertEqual(config.schema_name, "test_db")

class TestORMSQLConfig(unittest.TestCase):
    def test_orm_sql_config_initialization(self):
        config = ORMSQLConfig(host="localhost", port=5432, username="user", password="pass", schema_name="test_db", db_module_path="path.to.module")
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.username, "user")
        self.assertEqual(config.password, "pass")
        self.assertEqual(config.schema_name, "test_db")
        self.assertEqual(config.db_module_path, "path.to.module")

if __name__ == "__main__":
    unittest.main()
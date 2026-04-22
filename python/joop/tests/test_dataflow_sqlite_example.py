"""Tests for the working local SQLite dataflow example.

These tests create real SQLite database files on the local filesystem.
Each test uses a fresh temporary directory containing:
    - one primary SQLite database file
    - one fallback/cache SQLite database file

The files are configured into the example flow during ``setUp`` and are removed
when ``tearDown`` cleans up the temporary directory.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from joop.dataflow.examples.sqlite import (
    LocalSQLiteDataFlow,
    LocalSQLiteDataLink,
    SQLiteExamplePayload,
    SQLiteFallbackDataCatcher,
    SQLitePrimaryDataCatcher,
)


class TestSQLiteDataFlowExample(unittest.TestCase):
    def setUp(self):
        # These are real on-disk SQLite databases, not mocks or in-memory
        # stand-ins. We isolate them per test so replay/cached-record counts
        # are never influenced by earlier runs.
        self.temp_dir = TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.primary_path = str(base / "primary.sqlite")
        self.fallback_path = str(base / "fallback.sqlite")

        LocalSQLiteDataFlow.configure_paths(
            primary_path=self.primary_path,
            fallback_path=self.fallback_path,
        )
        LocalSQLiteDataFlow.reset()

    def tearDown(self):
        # Removing the temp directory also removes the SQLite database files
        # created by the example during the test.
        self.temp_dir.cleanup()

    def test_publish_success_writes_to_primary(self):
        # A healthy primary catcher should bypass the fallback store entirely.
        result = LocalSQLiteDataFlow.publish(SQLiteExamplePayload(id=1, message="hello"))
        self.assertEqual(result, ["primary-stored"])
        delivered = SQLitePrimaryDataCatcher.get_delivered_records()
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0].id, 1)
        self.assertEqual(delivered[0].message, "hello")

    def test_fallback_path_writes_to_sqlite_cache(self):
        # Force the primary destination down so the link must cache locally.
        LocalSQLiteDataLink.primary_should_fail = True
        result = LocalSQLiteDataFlow.publish(SQLiteExamplePayload(id=2, message="fallback"))
        self.assertEqual(result, ["fallback-cached"])
        self.assertEqual(LocalSQLiteDataLink.get_number_of_cached_records(), 1)
        cached = SQLiteFallbackDataCatcher.get_cached_records()
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0].model_type, "SQLiteExamplePayload")
        self.assertIn('"id":2', cached[0].payload_json)

    def test_replay_moves_cached_rows_to_primary_and_clears_cache(self):
        # First cache a record by failing the primary destination.
        LocalSQLiteDataLink.primary_should_fail = True
        LocalSQLiteDataFlow.publish(SQLiteExamplePayload(id=3, message="replay"))
        self.assertEqual(LocalSQLiteDataLink.get_number_of_cached_records(), 1)

        # Then restore the primary and verify replay drains the fallback store.
        LocalSQLiteDataLink.primary_should_fail = False
        replay_result = LocalSQLiteDataFlow.replay()

        self.assertEqual(replay_result, [1])
        self.assertEqual(LocalSQLiteDataLink.get_number_of_cached_records(), 0)
        delivered = SQLitePrimaryDataCatcher.get_delivered_records()
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0].id, 3)
        self.assertEqual(delivered[0].message, "replay")

    def test_flow_replay_skips_when_no_cached_rows_exist(self):
        # DataFlow.replay should not call into a link whose cache count is zero.
        replay_result = LocalSQLiteDataFlow.replay()
        self.assertEqual(replay_result, [])


if __name__ == "__main__":
    unittest.main()

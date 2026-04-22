import unittest
from dataclasses import dataclass

from sqlmodel import SQLModel

from joop.dataflow import (
    Capabilities,
    DataCatcher,
    DataFlow,
    DataLink,
    RetryDecision,
    RetryPolicy,
    SQLDBDataCatcher,
)
from joop.net import Credential
from joop.sql import SQLConfig, SQLScheme


class TestModel(SQLModel):
    id: int


class WrongModel(SQLModel):
    id: int


@dataclass
class PrimaryCatcher(DataCatcher):
    name: str = "primary"

    @classmethod
    def replay_to(cls, target_catcher: DataCatcher, model_type):
        return None

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        return 0


@dataclass
class FallbackCatcher(DataCatcher):
    name: str = "fallback"

    replay_calls = []
    cached_record_count = 0

    @classmethod
    def reset(cls):
        cls.replay_calls = []
        cls.cached_record_count = 0

    @classmethod
    def replay_to(cls, target_catcher: DataCatcher, model_type: SQLModel):
        cls.replay_calls.append((target_catcher, model_type))
        return "replayed-fallback"

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        return cls.cached_record_count


@dataclass
class RecordingFallbackCatcher(DataCatcher):
    name: str = "recording-fallback"

    replay_calls = []
    cached_record_count = 0

    @classmethod
    def reset(cls):
        cls.replay_calls = []
        cls.cached_record_count = 0

    @classmethod
    def replay_to(cls, target_catcher: DataCatcher, model_type: SQLModel):
        cls.replay_calls.append((target_catcher, model_type))
        return "replayed-recording-fallback"

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        return cls.cached_record_count


@dataclass
class RelatedPrimaryCatcher(DataCatcher):
    capabilities = Capabilities(supports_related_models=True)
    name: str = "related-primary"

    @classmethod
    def replay_to(cls, target_catcher: DataCatcher, model_type : SQLModel):
        return None

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        return 0


@dataclass
class RelatedFallbackCatcher(DataCatcher):
    capabilities = Capabilities(supports_related_models=True)
    name: str = "related-fallback"

    @classmethod
    def replay_to(cls, target_catcher: DataCatcher, model_type: SQLModel):
        return None

    @classmethod
    def get_number_of_cached_records(cls) -> int:
        return 0


class RetryOncePolicy(RetryPolicy):
    @classmethod
    def on_failure(cls, model: SQLModel, attempt_number: int, exception: Exception) -> RetryDecision:
        if attempt_number == 1:
            return RetryDecision.RETRY
        return RetryDecision.FALLBACK


class FallbackPolicy(RetryPolicy):
    @classmethod
    def on_failure(cls, model: SQLModel, attempt_number: int, exception: Exception) -> RetryDecision:
        return RetryDecision.FALLBACK


class RetryLink(DataLink):
    _modeltype = TestModel
    _catcher_type = PrimaryCatcher
    _retry_policy_type = RetryOncePolicy
    _fallback_catcher_type = FallbackCatcher
    publish_calls = []
    failures_before_success = 1

    @classmethod
    def reset(cls):
        cls.publish_calls = []
        cls.failures_before_success = 1

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: SQLModel):
        cls.publish_calls.append((catcher, model))
        primary_attempts = len([
            call for call in cls.publish_calls if call[0] is PrimaryCatcher
        ])
        if catcher is PrimaryCatcher and primary_attempts <= cls.failures_before_success:
            raise RuntimeError("primary failure")
        return f"{catcher.__name__}-ok"

class FallbackLink(DataLink):
    _modeltype = TestModel
    _catcher_type = PrimaryCatcher
    _retry_policy_type = FallbackPolicy
    _fallback_catcher_type = FallbackCatcher
    publish_calls = []

    @classmethod
    def reset(cls):
        cls.publish_calls = []

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: SQLModel):
        cls.publish_calls.append((catcher, model))
        if catcher is PrimaryCatcher:
            raise RuntimeError("primary failure")
        return f"{catcher.__name__}-ok"

class RecordingLink(DataLink):
    _modeltype = TestModel
    _catcher_type = PrimaryCatcher
    _retry_policy_type = FallbackPolicy
    _fallback_catcher_type = RecordingFallbackCatcher
    publish_calls = []

    @classmethod
    def reset(cls):
        cls.publish_calls = []

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: SQLModel):
        cls.publish_calls.append((catcher, model))
        return f"{catcher.__name__}-ok"

class RelatedLink(DataLink):
    _modeltype = TestModel
    _catcher_type = RelatedPrimaryCatcher
    _retry_policy_type = FallbackPolicy
    _fallback_catcher_type = RelatedFallbackCatcher
    _requires_related_models = True

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: SQLModel):
        return f"{catcher.__name__}-ok"

class InvalidRelatedLink(DataLink):
    _modeltype = TestModel
    _catcher_type = PrimaryCatcher
    _retry_policy_type = FallbackPolicy
    _fallback_catcher_type = FallbackCatcher
    _requires_related_models = True

    @classmethod
    def _publish_to_catcher(cls, catcher: DataCatcher, model: SQLModel):
        return f"{catcher.__name__}-ok"

class MultiLinkFlow(DataFlow):
    _modeltype = TestModel
    _link_types = [RetryLink, RecordingLink]


class SingleFallbackFlow(DataFlow):
    _modeltype = TestModel
    _link_types = [FallbackLink]


class InvalidRelatedFlow(DataFlow):
    _modeltype = TestModel
    _link_types = [InvalidRelatedLink]


class TestDataFlow(unittest.TestCase):
    def setUp(self):
        FallbackCatcher.reset()
        RecordingFallbackCatcher.reset()
        RetryLink.reset()
        FallbackLink.reset()
        RecordingLink.reset()

    def test_capabilities_json_backup_is_derived(self):
        related = Capabilities(supports_related_models=True)
        discrete = Capabilities(supports_related_models=False)
        self.assertTrue(related.supports_json_backup)
        self.assertFalse(discrete.supports_json_backup)

    def test_retrypolicy_rejects_use(self):
        with self.assertRaises(TypeError):
            RetryPolicy()

    def test_abstract_datalink_rejects_use(self):
        with self.assertRaises(NotImplementedError):
            class IncompleteLink(DataLink):
                _modeltype = TestModel
                _catcher_type = PrimaryCatcher
                _retry_policy_type = FallbackPolicy
                _fallback_catcher_type = FallbackCatcher

    def test_abstract_dataflow_rejects_use(self):
        class IncompleteFlow(DataFlow):
            pass

        with self.assertRaises(NotImplementedError):
            IncompleteFlow.publish(TestModel(id=1))

    def test_publish_accepts_declared_model_type(self):
        result = MultiLinkFlow.publish(TestModel(id=1))
        self.assertEqual(result, ["PrimaryCatcher-ok", "PrimaryCatcher-ok"])

    def test_publish_rejects_wrong_model_type(self):
        with self.assertRaises(TypeError):
            MultiLinkFlow.publish(WrongModel(id=1))

    def test_publish_retries_after_primary_failure(self):
        result = RetryLink.publish(TestModel(id=1))
        self.assertEqual(result, "PrimaryCatcher-ok")
        self.assertEqual(len(RetryLink.publish_calls), 2)
        self.assertEqual(RetryLink.publish_calls[0][0], PrimaryCatcher)
        self.assertEqual(RetryLink.publish_calls[1][0], PrimaryCatcher)

    def test_publish_routes_to_link_local_fallback_when_policy_says_so(self):
        result = FallbackLink.publish(TestModel(id=1))
        self.assertEqual(result, "FallbackCatcher-ok")
        self.assertEqual(len(FallbackLink.publish_calls), 2)
        self.assertEqual(FallbackLink.publish_calls[0][0], PrimaryCatcher)
        self.assertEqual(FallbackLink.publish_calls[1][0], FallbackCatcher)

    def test_replay_exists_and_is_callable_per_link(self):
        FallbackCatcher.cached_record_count = 1
        result = FallbackLink.replay()
        self.assertEqual(result, "replayed-fallback")
        self.assertEqual(len(FallbackCatcher.replay_calls), 1)
        self.assertEqual(FallbackCatcher.replay_calls[0][0], PrimaryCatcher)
        self.assertEqual(FallbackCatcher.replay_calls[0][1], TestModel)

    def test_flow_replay_calls_each_link(self):
        FallbackCatcher.cached_record_count = 1
        RecordingFallbackCatcher.cached_record_count = 0
        result = MultiLinkFlow.replay()
        self.assertEqual(result, ["replayed-fallback"])

    def test_related_model_capability_mismatch_is_rejected(self):
        with self.assertRaises(TypeError):
            InvalidRelatedFlow.publish(TestModel(id=1))

    def test_related_model_capability_match_is_allowed(self):
        result = RelatedLink.publish(TestModel(id=1))
        self.assertEqual(result, "RelatedPrimaryCatcher-ok")

    def test_link_cached_record_count_delegates_to_fallback_catcher(self):
        FallbackCatcher.cached_record_count = 3
        self.assertEqual(FallbackLink.get_number_of_cached_records(), 3)


class TestSQLDBDataCatcher(unittest.TestCase):
    def test_sqldb_datacatcher_stores_sqlconfig(self):
        config = SQLConfig(
            scheme=SQLScheme.SQLITE,
            driver=None,
            host="localhost",
            port=None,
            credential=Credential(username="user", password="pass"),
            schema_name="cache_db",
        )
        catcher = SQLDBDataCatcher(sql_config=config)
        self.assertEqual(catcher.sql_config, config)
        self.assertFalse(catcher.__class__.get_capabilities().supports_related_models)
        self.assertFalse(catcher.__class__.get_capabilities().supports_json_backup)


if __name__ == "__main__":
    unittest.main()

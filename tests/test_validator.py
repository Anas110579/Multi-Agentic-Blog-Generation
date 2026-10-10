import json
from types import SimpleNamespace

import pytest

from blogboard.agents.validator_agent import agent as validator


def _state(revision_count: int = 0) -> dict[str, object]:
    return {
        "topic": "Reliable model serving",
        "content": "# Reliable model serving\n\nA useful article.",
        "domain": "ml",
        "date": "2026-10-05",
        "revision_count": revision_count,
    }


def _mock_validator_response(monkeypatch: pytest.MonkeyPatch, response: str) -> None:
    class FakeLLM:
        def invoke(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(content=response)

    class FakeLLMAgentService:
        def __init__(self, temperature: float) -> None:
            self.llm = FakeLLM()

    monkeypatch.setattr(validator, "LLMAgentService", FakeLLMAgentService)


def test_invalid_validator_json_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_validator_response(monkeypatch, "not json")

    with pytest.raises(ValueError, match="refusing to publish"):
        validator.validator_node(_state())


def test_rejected_draft_requests_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_validator_response(
        monkeypatch,
        json.dumps({"approved": False, "feedback": "Add source citations."}),
    )

    result = validator.validator_node(_state())

    assert result["revision_needed"] is True
    assert result["validator_feedback"] == "Add source citations."
    assert result["revision_count"] == 1


def test_draft_rejected_after_revision_limit_is_not_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_validator_response(
        monkeypatch,
        json.dumps({"approved": False, "feedback": "Still needs sources."}),
    )

    with pytest.raises(RuntimeError, match="refusing to publish"):
        validator.validator_node(_state(revision_count=validator.MAX_REVISIONS))


def test_storage_failure_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_validator_response(
        monkeypatch,
        json.dumps({
            "approved": True,
            "title": "Reliable Model Serving",
            "description": "A practical guide to reliable model serving.",
            "slug": "Reliable Model Serving!",
        }),
    )

    class FailedStorage:
        def put_object(self, key: str, data: str, content_type: str) -> bool:
            return False

    monkeypatch.setattr(validator, "R2StorageService", FailedStorage)

    with pytest.raises(RuntimeError, match="Failed to upload article Markdown"):
        validator.validator_node(_state())


def test_approved_article_updates_markdown_and_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_validator_response(
        monkeypatch,
        json.dumps({
            "approved": True,
            "title": "Reliable Model Serving",
            "description": "A practical guide to reliable model serving.",
            "slug": "Reliable Model Serving!",
        }),
    )

    class FakeStorage:
        def __init__(self) -> None:
            self.uploads: list[tuple[str, str, str]] = []
            self.saved_articles: list[dict[str, object]] = []

        def put_object(self, key: str, data: str, content_type: str) -> bool:
            self.uploads.append((key, data, content_type))
            return True

        def get_articles_json(self, domain: str) -> list[dict[str, object]]:
            return []

        def save_articles_json(
            self, domain: str, articles: list[dict[str, object]]
        ) -> bool:
            self.saved_articles = articles
            return True

    storage = FakeStorage()
    monkeypatch.setattr(validator, "R2StorageService", lambda: storage)

    result = validator.validator_node(_state())

    assert result["slug"] == "reliable-model-serving"
    assert result["md_path"] == "r2://blogs/ml/reliable-model-serving.md"
    assert storage.uploads == [
        (
            "blogs/ml/reliable-model-serving.md",
            "# Reliable model serving\n\nA useful article.",
            "text/markdown",
        )
    ]
    assert storage.saved_articles[0]["id"] == "blogs/ml/reliable-model-serving.md"


def test_article_index_failure_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_validator_response(
        monkeypatch,
        json.dumps({
            "approved": True,
            "title": "Reliable Model Serving",
            "description": "A practical guide to reliable model serving.",
            "slug": "reliable-model-serving",
        }),
    )

    class FailedIndexStorage:
        def put_object(self, key: str, data: str, content_type: str) -> bool:
            return True

        def get_articles_json(self, domain: str) -> list[dict[str, object]]:
            return []

        def save_articles_json(
            self, domain: str, articles: list[dict[str, object]]
        ) -> bool:
            return False

    monkeypatch.setattr(validator, "R2StorageService", FailedIndexStorage)

    with pytest.raises(RuntimeError, match="Failed to update the R2 article index"):
        validator.validator_node(_state())

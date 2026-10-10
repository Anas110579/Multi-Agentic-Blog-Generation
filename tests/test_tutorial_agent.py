from types import SimpleNamespace

from blogboard.agents.tutorial_agent import agent as tutorial


def test_explicit_topic_generation_does_not_require_r2(
    monkeypatch,
) -> None:
    class FakeLLMAgentService:
        def __init__(self, temperature: float) -> None:
            self.llm = self

        def invoke(self, prompt: str) -> SimpleNamespace:
            return SimpleNamespace(content="# Feature Scaling\n\nGenerated test draft.")

    def fail_if_storage_is_created() -> None:
        raise AssertionError("R2 should not be initialized for an explicit topic.")

    monkeypatch.setattr(tutorial, "LLMAgentService", FakeLLMAgentService)
    monkeypatch.setattr(tutorial, "R2StorageService", fail_if_storage_is_created)

    result = tutorial.tutorial_node({
        "topic": "Feature scaling",
        "domain": "ml",
        "subtopics": "Standardization and normalization",
    })

    assert result["content"] == "# Feature Scaling\n\nGenerated test draft."
    assert result["read_time"] == "1 min"

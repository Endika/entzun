from __future__ import annotations

from typing import Any

from entzun.adapters.openai_client import OpenAIMeetingSummarizer, OpenAISentimentAnalyzer


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = type("Msg", (), {"content": content})


class _FakeChatCompletions:
    def __init__(self, content: str) -> None:
        self._content = content
        self.sent: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return type("Resp", (), {"choices": [_FakeChoice(self._content)]})


class _FakeOpenAI:
    def __init__(self, content: str) -> None:
        self.chat = type("Chat", (), {"completions": _FakeChatCompletions(content)})


def test_openai_sentiment_analyzer_parses_score_and_summary() -> None:
    content = "SCORE: 5\nSUMMARY: Team is optimistic about the release."
    client = _FakeOpenAI(content)
    analyzer = OpenAISentimentAnalyzer(client=client, recent_context=[], max_context_items=5)

    score, summary = analyzer.analyze("We are happy with the progress.", [])

    assert score == 5
    assert "optimistic" in summary


def test_openai_sentiment_analyzer_returns_zero_for_short_text() -> None:
    client = _FakeOpenAI("SCORE: 3\nSUMMARY: short text")
    analyzer = OpenAISentimentAnalyzer(client=client, recent_context=[], max_context_items=5)

    score, summary = analyzer.analyze("ok", [])

    assert score == 0
    assert summary == ""


def test_openai_meeting_summarizer_returns_content() -> None:
    expected = "This is a synthetic executive summary."
    client = _FakeOpenAI(expected)
    summarizer = OpenAIMeetingSummarizer(client=client)

    result = summarizer.summarize_full(
        "Transcript",
        avg_sentiment=1.5,
        num_utterances=3,
        language="en",
    )

    assert result == expected


def test_openai_adapters_ask_gpt_6_luna_with_reasoning_off() -> None:
    sentiment_client = _FakeOpenAI("SCORE: 1\nSUMMARY: fine")
    OpenAISentimentAnalyzer(
        client=sentiment_client, recent_context=[], max_context_items=5
    ).analyze("We are happy with the progress.", [])
    summary_client = _FakeOpenAI("summary")
    OpenAIMeetingSummarizer(client=summary_client).summarize_full(
        "Transcript", avg_sentiment=1.5, num_utterances=3
    )

    for client in (sentiment_client, summary_client):
        request = client.chat.completions.sent[0]
        assert request["model"] == "gpt-6-luna"
        assert request["reasoning_effort"] == "none"

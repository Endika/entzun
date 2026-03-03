from __future__ import annotations

from typing import Any

from entzun.ui.app import EntzunApp


class _FakeSentimentAnalyzer:
    def __init__(self, score: int, summary: str, should_raise: bool = False) -> None:
        self.score = score
        self.summary = summary
        self.should_raise = should_raise
        self.calls: list[tuple[str, list[str]]] = []

    def analyze(self, text: str, context: list[str] | None = None) -> tuple[int, str]:  # noqa: ARG002
        if self.should_raise:
            raise RuntimeError("boom")
        self.calls.append((text, context or []))
        return self.score, self.summary


class _FakeLine:
    def __init__(self) -> None:
        self.data: tuple[list[int], list[int]] | None = None
        self.color: str | None = None

    def set_data(self, x_data: Any, y_data: Any) -> None:
        self.data = (list(x_data), list(y_data))

    def set_color(self, color: str) -> None:
        self.color = color


class _FakeAxis:
    def __init__(self) -> None:
        self.xlim: tuple[int, int] | None = None

    def set_xlim(self, left: int, right: int) -> None:
        self.xlim = (left, right)


class _FakeCanvas:
    def __init__(self) -> None:
        self.draw_calls = 0

    def draw(self) -> None:
        self.draw_calls += 1


def _make_partial_app() -> EntzunApp:
    app = EntzunApp.__new__(EntzunApp)  # type: ignore[call-arg]
    app.recent_context = []
    app.sentiment_analyzer = _FakeSentimentAnalyzer(5, "summary")  # type: ignore[assignment]
    app._status_messages: list[str] = []

    def fake_log_status(message: str) -> None:
        app._status_messages.append(message)

    app.log_status = fake_log_status  # type: ignore[assignment]
    return app


class _FakeVar:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


def test_analizar_texto_returns_analyzer_result_and_logs() -> None:
    app = _make_partial_app()

    score, summary = app.analizar_texto("Some long enough text")

    assert score == 5
    assert summary == "summary"
    assert any("[AI] Analysing with AI..." in msg for msg in app._status_messages)
    assert any("Analysis completed" in msg for msg in app._status_messages)


def test_analizar_texto_handles_exceptions() -> None:
    app = _make_partial_app()
    app.sentiment_analyzer = _FakeSentimentAnalyzer(0, "", should_raise=True)  # type: ignore[assignment]
    app._status_messages = []

    score, summary = app.analizar_texto("Some long enough text")

    assert score == 0
    assert summary == "Error while analysing."
    assert any("Error analysing" in msg for msg in app._status_messages)


def test_update_graph_appends_and_sets_color_and_limits() -> None:
    app = _make_partial_app()
    app.sentiment_history = []
    app.line = _FakeLine()  # type: ignore[assignment]
    app.ax = _FakeAxis()  # type: ignore[assignment]
    app.canvas = _FakeCanvas()  # type: ignore[assignment]

    app.update_graph(3)
    app.update_graph(-2)
    app.update_graph(5)

    assert app.sentiment_history == [3, -2, 5]
    assert app.line.data is not None
    x_data, y_data = app.line.data
    assert y_data == [3, -2, 5]
    assert x_data == list(range(len(y_data)))
    assert app.ax.xlim == (0, max(10, len(y_data)))
    assert app.line.color in {"green", "red"}
    assert app.canvas.draw_calls == 3


def test_change_transcription_service_switches_flag_and_logs() -> None:
    app = _make_partial_app()
    app.transcription_var = _FakeVar("whisper")  # type: ignore[assignment]
    app.use_whisper_api = False

    app.change_transcription_service()

    assert app.use_whisper_api is True
    assert any("[SERVICE]" in msg for msg in app._status_messages)


def test_change_language_sets_current_language_and_logs() -> None:
    app = _make_partial_app()
    app.lang_var = _FakeVar("en")  # type: ignore[assignment]
    app.current_language = "es-ES"

    app.change_language()

    assert app.current_language == "en"
    assert any("[LANG] Language: English" in msg for msg in app._status_messages)

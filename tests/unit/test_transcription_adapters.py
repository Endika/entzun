from __future__ import annotations

from typing import Any

import httpx2
import pytest
import speech_recognition as sr
from openai import OpenAI
from pydub import AudioSegment

from entzun.adapters.transcription import GoogleTranscriptionAdapter, WhisperTranscriptionAdapter


class _FakeRecognizer(sr.Recognizer):
    def __init__(self, returned_text: str) -> None:
        super().__init__()
        self._returned_text = returned_text
        self.last_language: str | None = None

    def recognize_google(self, audio_data: Any, language: str | None = None) -> str:  # noqa: ARG002
        self.last_language = language
        return self._returned_text


class _CannedTranscriptionServer:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        request.read()
        self.requests.append(request)
        return httpx2.Response(200, json=self._body)

    def form_fields(self) -> list[tuple[str, str]]:
        (request,) = self.requests
        boundary = request.headers["content-type"].split("boundary=")[1].encode()
        fields: list[tuple[str, str]] = []
        for part in request.content.split(b"--" + boundary):
            head, _, value = part.partition(b"\r\n\r\n")
            if b'name="' not in head or b"filename=" in head:
                continue
            name = head.split(b'name="')[1].split(b'"')[0].decode()
            fields.append((name, value.removesuffix(b"\r\n").decode()))
        return fields


def _client_for(server: _CannedTranscriptionServer) -> OpenAI:
    return OpenAI(
        api_key="test-key",
        base_url="https://api.test/v1",
        http_client=httpx2.Client(transport=httpx2.MockTransport(server)),
        max_retries=0,
    )


@pytest.fixture
def _no_mp3_encoder(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_export(self: AudioSegment, out_f: Any, format: str = "mp3") -> None:  # noqa: ARG002
        out_f.write(b"dummy")

    monkeypatch.setattr(AudioSegment, "export", fake_export, raising=False)


def _make_fake_audio() -> sr.AudioData:
    # 1 second of silence, 16-bit mono @ 16kHz
    raw = b"\x00\x00" * 16000
    return sr.AudioData(raw, sample_rate=16000, sample_width=2)


def test_google_transcription_adapter_uses_language_code() -> None:
    recognizer = _FakeRecognizer("hello world")
    adapter = GoogleTranscriptionAdapter(recognizer)
    audio = _make_fake_audio()

    text = adapter.transcribe(audio, "en-US")

    assert text == "hello world"
    assert recognizer.last_language == "en-US"


@pytest.mark.usefixtures("_no_mp3_encoder")
def test_openai_adapter_posts_gpt_transcribe_as_json_and_returns_text() -> None:
    server = _CannedTranscriptionServer(
        {"text": "  kaixo mundua \n", "languages": [{"code": "eu"}]}
    )
    adapter = WhisperTranscriptionAdapter(_client_for(server))

    text = adapter.transcribe(_make_fake_audio(), "en")

    assert text == "kaixo mundua"
    (request,) = server.requests
    assert request.url.path == "/v1/audio/transcriptions"
    fields = server.form_fields()
    assert ("model", "gpt-transcribe") in fields
    assert ("response_format", "json") in fields


@pytest.mark.usefixtures("_no_mp3_encoder")
@pytest.mark.parametrize(
    ("language_code", "expected"), [("es", "es"), ("en-US", "en"), ("eu", "eu")]
)
def test_openai_adapter_sends_language_as_languages_array(
    language_code: str, expected: str
) -> None:
    server = _CannedTranscriptionServer({"text": "ok"})
    adapter = WhisperTranscriptionAdapter(_client_for(server))

    adapter.transcribe(_make_fake_audio(), language_code)

    fields = server.form_fields()
    assert ("languages[]", expected) in fields
    assert all(name != "language" for name, _ in fields)


@pytest.mark.usefixtures("_no_mp3_encoder")
@pytest.mark.parametrize("language_code", ["auto", None])
def test_openai_adapter_omits_languages_for_auto_detection(language_code: str | None) -> None:
    server = _CannedTranscriptionServer({"text": "ok"})
    adapter = WhisperTranscriptionAdapter(_client_for(server))

    adapter.transcribe(_make_fake_audio(), language_code)

    names = [name for name, _ in server.form_fields()]
    assert "languages[]" not in names
    assert "language" not in names

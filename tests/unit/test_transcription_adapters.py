from __future__ import annotations

from typing import Any

import speech_recognition as sr
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


class _FakeTranscriptions:
    def __init__(self, returned_text: str) -> None:
        self._returned_text = returned_text

    def create(self, **_: Any) -> str:
        return self._returned_text


class _FakeAudioClient:
    def __init__(self, returned_text: str) -> None:
        self.transcriptions = _FakeTranscriptions(returned_text)


class _FakeOpenAI:
    def __init__(self, returned_text: str) -> None:
        self.audio = _FakeAudioClient(returned_text)


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


def test_whisper_transcription_adapter_returns_text(monkeypatch: Any) -> None:
    def fake_export(self: AudioSegment, out_f: Any, format: str = "mp3") -> None:  # noqa: ARG002
        out_f.write(b"dummy")

    monkeypatch.setattr(AudioSegment, "export", fake_export, raising=False)
    client = _FakeOpenAI("transcribed text")
    adapter = WhisperTranscriptionAdapter(client)
    audio = _make_fake_audio()

    text = adapter.transcribe(audio, "en")

    assert text == "transcribed text"

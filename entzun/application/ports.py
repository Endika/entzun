from __future__ import annotations

from typing import Protocol

import speech_recognition as sr


class SentimentAnalyzerPort(Protocol):
    def analyze(
        self,
        text: str,
        context: list[str],
        language: str | None = None,
    ) -> tuple[int, str]: ...


class MeetingSummarizerPort(Protocol):
    def summarize_full(
        self,
        transcript: str,
        avg_sentiment: float,
        num_utterances: int,
        language: str | None = None,
    ) -> str: ...


class TranscriptionPort(Protocol):
    def transcribe(self, audio: sr.AudioData, language_code: str | None) -> str: ...

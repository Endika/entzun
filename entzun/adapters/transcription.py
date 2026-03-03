from __future__ import annotations

import io
from typing import cast

import speech_recognition as sr
from openai import OpenAI
from pydub import AudioSegment

from entzun.application.ports import TranscriptionPort


class GoogleTranscriptionAdapter(TranscriptionPort):
    def __init__(self, recognizer: sr.Recognizer) -> None:
        self._recognizer = recognizer

    def transcribe(self, audio: sr.AudioData, language_code: str | None) -> str:
        google_lang = language_code
        if google_lang:
            result = self._recognizer.recognize_google(audio, language=google_lang)
        else:
            result = self._recognizer.recognize_google(audio)
        return cast(str, result)


class WhisperTranscriptionAdapter(TranscriptionPort):
    def __init__(self, client: OpenAI) -> None:
        self._client = client

    def transcribe(self, audio: sr.AudioData, language_code: str | None) -> str:
        audio_data = io.BytesIO(audio.get_wav_data())
        audio_segment = AudioSegment.from_wav(audio_data)

        mp3_buffer = io.BytesIO()
        audio_segment.export(mp3_buffer, format="mp3")
        mp3_buffer.seek(0)
        mp3_buffer.name = "audio.mp3"

        whisper_lang = language_code
        if whisper_lang and whisper_lang != "auto":
            language = whisper_lang if len(whisper_lang) == 2 else whisper_lang.split("-")[0][:2]
        else:
            language = None

        if language is not None:
            transcript = self._client.audio.transcriptions.create(
                file=mp3_buffer,
                model="whisper-1",
                response_format="text",
                language=language,
            )
        else:
            transcript = self._client.audio.transcriptions.create(
                file=mp3_buffer,
                model="whisper-1",
                response_format="text",
            )

        return transcript.strip()

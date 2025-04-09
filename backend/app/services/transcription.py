import os
import tempfile
import warnings
from typing import BinaryIO

import whisper

# Suprimir la advertencia específica de FP16 no soportado en CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")


class TranscriptionService:
    def __init__(self, model_name: str = "base"):
        self.model = whisper.load_model(model_name)
    
    async def transcribe_audio(self, audio_data: BinaryIO) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            audio_data.seek(0)
            chunk_size = 8192
            while True:
                chunk = audio_data.read(chunk_size)
                if not chunk:
                    break
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            result = self.model.transcribe(temp_path)
            return result["text"]
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


transcription_service = TranscriptionService() 
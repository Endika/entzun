import asyncio
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Form, Query
from fastapi.responses import StreamingResponse

from app.api.models import TranscriptionResponse
from app.services.report_generator import report_generator
from app.services.transcription import transcription_service

router = APIRouter()


@router.post("/", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., max_size=50_000_000),
    report_type: Optional[str] = Form("standard", description="Type of report to generate: standard, executive, detailed, or action")
):
    try:
        # Create a copy of the file content
        contents = await audio.read()
        
        # Create a fresh BytesIO object
        from io import BytesIO
        audio_bytes = BytesIO(contents)
        
        transcript = await transcription_service.transcribe_audio(audio_bytes)
        
        report = await report_generator.generate_report(
            transcript,
            report_type=report_type
        )
        
        return TranscriptionResponse(transcript=transcript, report=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_transcribe_audio(
    audio: UploadFile = File(..., max_size=50_000_000),
    report_type: Optional[str] = Form("standard", description="Type of report to generate: standard, executive, detailed, or action")
):
    # Create a copy of the file content
    contents = await audio.read()
    
    # Create BytesIO object outside the streaming function
    from io import BytesIO
    audio_bytes = BytesIO(contents)
    
    # Process transcription before streaming starts
    transcript = await transcription_service.transcribe_audio(audio_bytes)
    report = await report_generator.generate_report(transcript, report_type=report_type)
    
    async def stream_results():
        try:
            yield f"Transcript: {transcript}\n\n"
            yield f"Report: {report}\n"
        except Exception as e:
            yield f"Error: {str(e)}"
    
    return StreamingResponse(stream_results(), media_type="text/plain")
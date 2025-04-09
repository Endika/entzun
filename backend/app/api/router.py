from fastapi import APIRouter

from app.api import transcription

api_router = APIRouter()
 
api_router.include_router(
    transcription.router,
    prefix="/transcription",
    tags=["transcription"]
) 
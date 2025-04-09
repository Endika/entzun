from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.datastructures import UploadFile as UploadFileClass

from app.api.router import api_router
from app.core.config import settings

UploadFileClass.max_size = 100 * 1024 * 1024  # 100 MB

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Entzun Audio Transcription API. Go to /docs for the documentation."} 
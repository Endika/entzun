from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    transcript: str
    report: str


class ErrorResponse(BaseModel):
    detail: str 
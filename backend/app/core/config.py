from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Audio Transcription API"
    API_V1_STR: str = "/api/v1"
    
    OPENAI_API_KEY: str
    
    MAX_HISTORY_SIZE: int = 10_000  # Characters
    SUMMARIZE_AFTER: int = 8_000  # Characters

    class Config:        
        env_file = ".env"
        case_sensitive = True


settings = Settings() 
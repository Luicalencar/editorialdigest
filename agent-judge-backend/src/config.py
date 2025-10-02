import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    analyzer_user: str = os.getenv("ANALYZER_USER", "admin")
    analyzer_pass: str = os.getenv("ANALYZER_PASS", "changeme")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    agent_version: str = os.getenv("AGENT_VERSION", "v1")
    use_mock_openai: bool = os.getenv("USE_MOCK_OPENAI", "0") in ("1", "true", "True")

def get_settings() -> Settings:
    return Settings()



from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import DirectoryPath

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Project Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    INBOX_DIR: DirectoryPath = BASE_DIR / "01_Inbox"
    REVIEW_DIR: DirectoryPath = BASE_DIR / "02_Review"
    MATERIALS_DIR: DirectoryPath = BASE_DIR / "materials"

    # Orchestrator
    TASKIQ_BROKER_URL: str = "sqlite://db.sqlite3"
    
    # External Worker (GPT-SoVITS)
    GPT_SOVITS_PYTHON_PATH: Path = BASE_DIR / "worker" / ".gpt_venv" / "bin" / "python3"
    GPT_SOVITS_API_URL: str = "http://localhost:9880"

    # Performance
    MAX_CONCURRENT_AUDIO_JOBS: int = 5

settings = Settings()

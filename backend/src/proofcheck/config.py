from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROOFCHECK_", env_file=".env", extra="ignore")

    ollama_url: str = "http://127.0.0.1:11434"
    vision_model: str = "gemma3:4b"
    vision_timeout_s: float = 90.0
    # Loopback only by default: the whole point is that statements stay on this machine.
    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()

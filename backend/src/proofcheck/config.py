from functools import lru_cache
from typing import Self
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROOFCHECK_", env_file=".env", extra="ignore")

    ollama_url: str = "http://127.0.0.1:11434"
    vision_model: str = "gemma3:4b"
    vision_timeout_s: float = 90.0
    # Loopback only by default: the whole point is that statements stay on this machine.
    host: str = "127.0.0.1"
    port: int = 8000
    # Set PROOFCHECK_ALLOW_LAN=true to knowingly serve other devices on your network.
    allow_lan: bool = False

    @field_validator("ollama_url")
    @classmethod
    def _ollama_on_this_machine(cls, value: str) -> str:
        # Screenshots are sent to this URL. A stray .env pointing elsewhere would ship
        # people's payment details off the laptop, so refuse anything but loopback.
        if urlsplit(value).hostname not in LOOPBACK_HOSTS:
            raise ValueError("ollama_url must point at this machine (localhost / 127.0.0.1)")
        return value

    @model_validator(mode="after")
    def _listen_on_loopback(self) -> Self:
        if self.host not in LOOPBACK_HOSTS and not self.allow_lan:
            raise ValueError("host is not loopback; set allow_lan=true to serve your network")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

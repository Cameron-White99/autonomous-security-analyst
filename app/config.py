from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str | None = None
    database_url: str | None = None
    environment: str = "development"
    demo_mode: bool = False

    @property
    def use_demo_agents(self) -> bool:
        """Demo mode is active when explicitly enabled or when no API key is configured."""
        return self.demo_mode or not self.anthropic_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()

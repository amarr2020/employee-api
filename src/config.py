"""Application configuration loaded from environment variables."""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_base_url: str = "http://localhost"
    api_client_id: str
    api_client_secret: str
    api_username: str
    api_password: str

    database_url: str = "sqlite:///./employees.db"

    auth_header_type: str = "access-token"

    @property
    def token_url(self) -> str:
        return f"{self.api_base_url}/api/token/"

    @property
    def employees_url(self) -> str:
        return f"{self.api_base_url}/api/employee/list/"

    @property
    def db_path(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.replace("sqlite:///", "")
        return "employees.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

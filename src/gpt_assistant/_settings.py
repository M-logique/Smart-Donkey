from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        extra="allow", env_ignore_empty=False, env_file=".env"
    )

    TOKEN: str
    DATABASE_URL: str
    OWNERS: List[int]

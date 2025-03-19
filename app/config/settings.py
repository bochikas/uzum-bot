from functools import lru_cache

from dotenv import find_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(filename=".env", usecwd=True), env_file_encoding="utf-8", extra="ignore"
    )


class TelegramConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="tg_")

    token: SecretStr
    admin_id: str


class DatabaseConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="postgres_")

    host: str
    port: int
    user: str
    password: SecretStr
    name: str


class Config(BaseSettings):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    @property
    def database_uri(self) -> str:
        return f"postgresql+asyncpg://{self.db.user}:{self.db.password.get_secret_value()}@{self.db.host}:{self.db.port}/{self.db.name}"


@lru_cache
def get_app_config():
    return Config()


app_config = get_app_config()

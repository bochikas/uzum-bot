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
    db: str


class SchedulerConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="scheduler_")

    run_interval: int = 30  # minutes


class ParserConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="parser_")

    headless_mode: bool


class RabbitMQConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="rabbitmq_")

    host: str
    port: int
    default_user: str
    default_pass: str
    management_port: int

    exchange: str = "product.events"
    exchange_type: str = "direct"
    queue_product_add: str = "product.add"
    routing_key_product_add: str = "product.add"

    @property
    def rabbitmq_uri(self) -> str:
        return f"amqp://{self.default_user}:{self.default_pass}@{self.host}:{self.port}"


class Config(BaseConfig):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)

    min_check_interval: int = 60 * 8  # минут

    @property
    def database_uri(self) -> str:
        return f"postgresql+asyncpg://{self.db.user}:{self.db.password.get_secret_value()}@{self.db.host}:{self.db.port}/{self.db.db}"  # noqa


@lru_cache
def get_app_config():
    return Config()


app_config = get_app_config()

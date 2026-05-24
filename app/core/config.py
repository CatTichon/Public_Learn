from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./learning_bot.db", alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    content_generation_mode: str = Field(
        default="template", alias="CONTENT_GENERATION_MODE"
    )
    yandexgpt_api_key: str = Field(default="", alias="YANDEXGPT_API_KEY")
    yandexgpt_iam_token: str = Field(default="", alias="YANDEXGPT_IAM_TOKEN")
    yandexgpt_folder_id: str = Field(default="", alias="YANDEXGPT_FOLDER_ID")
    yandexgpt_model: str = Field(default="yandexgpt-lite", alias="YANDEXGPT_MODEL")
    yandexgpt_model_uri: str = Field(default="", alias="YANDEXGPT_MODEL_URI")
    yandexgpt_few_shot_examples: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "YANDEXGPT_FEW_SHOT_EXAMPLES",
            "YANDEXGPT_EXAMPLES_LIMIT",
        ),
    )
    yandexgpt_base_url: str = Field(
        default="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        alias="YANDEXGPT_BASE_URL",
    )
    yandexgpt_timeout_seconds: float = Field(
        default=20.0, alias="YANDEXGPT_TIMEOUT_SECONDS"
    )
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

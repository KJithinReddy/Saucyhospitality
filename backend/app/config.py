from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Saucy Hospitality"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite:///./runtime/saucy.db"
    upload_dir: str = "./runtime/uploads"

    max_image_bytes: int = 8 * 1024 * 1024
    max_video_bytes: int = 25 * 1024 * 1024

    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "http://localhost:3000"
    openrouter_app_title: str = "Saucy Hospitality"
    openrouter_timeout_seconds: float = 45.0

    demo_reset_token: str = "saucy-demo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-only-secret-key-change-me-before-deploying"
    database_url: str = "sqlite:///./data/taskboard.db"
    access_token_expire_minutes: int = 60 * 24 * 7
    algorithm: str = "HS256"


settings = Settings()

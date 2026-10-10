from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/agrisense"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "agrisense123"
    access_token_minutes: int = 60
    read_limit_per_min: int = 60 
    llm_provider: str = "fake" 
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    agent_daily_token_quota: int = 20000 
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

print("DATABASE URL:", settings.database_url)
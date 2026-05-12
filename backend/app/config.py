from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "riya"
    bolna_api_key: str = ""
    bolna_agent_id: str = ""
    bolna_webhook_secret: str = ""
    bolna_base_url: str = "https://api.bolna.ai"
    admin_token: str = "dev-admin-token"
    public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

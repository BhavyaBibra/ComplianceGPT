from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Central configuration and environment variables management.
    Uses pydantic BaseSettings to load from .env file or system environment.
    """
    # Supabase Configuration
    supabase_url: str = ""
    supabase_anon_key: str = ""
    
    # LLM & Embedding APIs
    jina_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Future scaling: Add database connection strings, model names, etc.
    # db_host: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Central settings object to be imported across the app
settings = Settings()

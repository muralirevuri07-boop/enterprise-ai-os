from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GROQ_API_KEY: str
    AGENTWATCH_API_KEY: str = ""
    AGENTWATCH_URL: str = "https://agentwatch-8eap.onrender.com"

    class Config:
        env_file = ".env"

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import computed_field

class Settings(BaseSettings):
    APP_NAME: str = "Smart-Query-Routing-Email-Automation-System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # n8n Webhook Configuration
    N8N_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = ""    
    N8N_INTERNAL_API_KEY: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    GEMINI_API_KEY_1: str = ""
    GEMINI_API_KEY_2: str = ""
    GEMINI_API_KEY_3: str = ""
    GEMINI_API_KEY_4: str = ""
    GEMINI_API_KEY_5: str = ""
    GEMINI_API_KEY_6: str = ""
    GEMINI_API_KEY_7: str = ""
    GEMINI_API_KEY_8: str = ""
    GEMINI_API_KEY_9: str = ""

    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GOOGLE_LOGIN_CLIENT_ID: str = ""
    
    @computed_field
    @property
    def GEMINI_API_KEYS(self) -> list[str]:
        return [
            key for key in [
                self.GEMINI_API_KEY_1,
                self.GEMINI_API_KEY_2,
                self.GEMINI_API_KEY_3,
                self.GEMINI_API_KEY_4,
                self.GEMINI_API_KEY_5,
                self.GEMINI_API_KEY_6,
                self.GEMINI_API_KEY_7,
                self.GEMINI_API_KEY_8,
                self.GEMINI_API_KEY_9,
            ]
            if key
        ]


settings = Settings()

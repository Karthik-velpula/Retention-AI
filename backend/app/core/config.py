from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Predictive Analytics for Student Retention"
    APP_ENV: str = "development"
    API_V1_STR: str = "/ren"
    APP_BASE_PATH: str = "/aistudent"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    DATABASE_URL: str | None = None
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "student_retention"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Predictive Analytics for Student Retention"
    SMTP_START_TLS: bool = True
    SMTP_VALIDATE_CERTS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 20
    CLIENT_URL: str = "https://160.187.169.41"
    PUBLIC_API_URL: str = "https://160.187.169.41/aistudent/ren"
    ALLOWED_HOSTS: str = "160.187.169.41,localhost,127.0.0.1"
    CORS_ORIGINS: str = ""
    FORCE_HTTPS: bool = False
    RUN_STARTUP_DB_INIT: bool = True
    GOOGLE_DRIVE_CREDENTIALS_PATH: str = "google-drive-credentials.json"
    GOOGLE_DRIVE_REPORT_FOLDER_ID: str = ""
    MODEL_DIR: str = "backend/models"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{quote_plus(self.MYSQL_USER)}:{quote_plus(self.MYSQL_PASSWORD)}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    @computed_field
    @property
    def MODEL_PATH(self) -> str:
        return str(self.MODEL_DIR_PATH / "student_retention_model.pkl")

    @computed_field
    @property
    def PREPROCESSOR_PATH(self) -> str:
        return str(self.MODEL_DIR_PATH / "preprocessor.pkl")

    @computed_field
    @property
    def LABEL_ENCODER_PATH(self) -> str:
        return str(self.MODEL_DIR_PATH / "label_encoder.pkl")

    @computed_field
    @property
    def FEATURE_COLUMNS_PATH(self) -> str:
        return str(self.MODEL_DIR_PATH / "feature_columns.pkl")

    @computed_field
    @property
    def MODEL_DIR_PATH(self) -> Path:
        raw = Path(self.MODEL_DIR)
        if raw.is_absolute():
            return raw
        return Path(__file__).resolve().parents[2] / "models"

    @computed_field
    @property
    def GOOGLE_DRIVE_CREDENTIALS_FILE(self) -> Path:
        raw = Path(self.GOOGLE_DRIVE_CREDENTIALS_PATH)
        if raw.is_absolute():
            return raw
        return Path(__file__).resolve().parents[2] / raw

    @computed_field
    @property
    def ALLOWED_HOSTS_LIST(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @computed_field
    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        if self.CORS_ORIGINS.strip():
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return [self.CLIENT_URL]

    @computed_field
    @property
    def API_PREFIX(self) -> str:
        return f"{self.APP_BASE_PATH.rstrip('/')}{self.API_V1_STR}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "ChangeMe!2026"
    ADMIN_EMAIL: str = "admin@example.com"
    # Email (approval requests). Leave SMTP_HOST empty to disable email.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 25
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = False
    SMTP_SSL: bool = False
    SMTP_FROM: str = "sims@localhost"
    PUBLIC_URL: str = "http://localhost"      # address approvers can open from their mail client
    APPROVAL_LINK_HOURS: int = 168
    PING_COUNT: int = 3
    PING_TIMEOUT: int = 2


settings = Settings()

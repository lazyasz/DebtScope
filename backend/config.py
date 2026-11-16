"""
Configuration module for Predictive Engineering Intelligence Platform.
Loads environment variables and provides centralized application settings.

Five-Weight Formula (viva-locked, sum = 1.00):
  w_TR = 0.35  (Technical Risk)
  w_BI = 0.30  (Business Impact)
  w_U  = 0.15  (Release Urgency)
  w_M  = 0.10  (Maintenance Cost)
  w_A  = 0.10  (Debt Age)

Stage-6 Effort Blend (separate post-processing step, NOT a 6th weight):
  w_E  = 0.15  → adjusts PS_base → PS_final; does NOT enter the 5D formula
"""

from typing import Annotated, List, Optional
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    # App Information
    PROJECT_NAME: str = "DebtScope — Predictive Engineering Intelligence"
    PROJECT_DESCRIPTION: str = (
        "Business-aware Decision Intelligence API for Technical Debt Prioritization"
    )
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Database Configuration (SQLite default for dev, PostgreSQL for production)
    DATABASE_URL: str = "sqlite:///./tech_debt_intelligence.db"

    # Security & CORS
    SECRET_KEY: str = "super-secret-key-change-in-production-2026"
    # FRONTEND_URL is always added in main.py. Override as a JSON list, e.g.
    # ALLOWED_ORIGINS='["https://app.example.com"]'. Never "*": cookies are sent cross-origin.
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8501",
    ]

    # ── Auth ──────────────────────────────────────────────────────────────────
    # DEV_SANDBOX_AUTH: bypass real Google OAuth for local/test use only.
    # MUST be False in production — a RuntimeError is raised if set True with
    # ENVIRONMENT=production.
    DEV_SANDBOX_AUTH: bool = False

    # Session cookie
    SESSION_COOKIE_NAME: str = "debtscope_session"
    SESSION_MAX_AGE_SECONDS: int = 28800  # 8 hours
    COOKIE_SECURE: Optional[bool] = None  # None -> auto-detect (True in production, False in dev)
    COOKIE_SAMESITE: str = "lax"

    # Token encryption for integration OAuth tokens at rest (Fernet key, base64url)
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: str = ""

    # ── Background Worker & Job Orchestration Limits ────────────────────────
    WORKER_MAX_GLOBAL_CONCURRENT_JOBS: int = 2
    WORKER_MAX_WORKSPACE_CONCURRENT_JOBS: int = 1
    WORKER_JOB_TIMEOUT_SECONDS: int = 600
    WORKER_HEARTBEAT_STALE_SECONDS: int = 120

    # ── Priority Engine Weights — 5D Formula (sum = 1.00, viva-locked) ───────
    WEIGHT_TECHNICAL_RISK: float = Field(default=0.35, ge=0.0, le=1.0)
    WEIGHT_BUSINESS_IMPACT: float = Field(default=0.30, ge=0.0, le=1.0)
    WEIGHT_RELEASE_URGENCY: float = Field(default=0.15, ge=0.0, le=1.0)
    WEIGHT_MAINTENANCE_COST: float = Field(default=0.10, ge=0.0, le=1.0)
    WEIGHT_DEBT_AGE: float = Field(default=0.10, ge=0.0, le=1.0)

    # Stage-6 effort blend (post-processing ONLY — NOT one of the five weights)
    EFFORT_BLEND_WEIGHT: float = Field(default=0.15, ge=0.0, le=1.0)

    # Production & Deployment Settings
    FRONTEND_URL: str = "http://localhost:5173"
    JWT_SECRET: str = "pei-jwt-secret-key-production-2026"
    SANDBOX_MODE: bool = False  # Legacy alias — prefer DEV_SANDBOX_AUTH

    # Integrations: Google OAuth (Server-Side Authorization Code Flow)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Integrations: GitHub App & OAuth
    GITHUB_TOKEN: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # Integrations: Atlassian Jira Cloud (OAuth 2.0 3LO & REST API)
    JIRA_SIMULATION_MODE: bool = False  # Explicit flag; must be False in production
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    JIRA_REDIRECT_URI: str = "http://localhost:5173/auth/jira/callback"
    JIRA_BASE_URL: str = ""
    JIRA_DOMAIN: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = "DEBT"

    # Integrations: Notion (OAuth 2.0 & REST API v1)
    NOTION_SIMULATION_MODE: bool = False  # Explicit flag; must be False in production
    NOTION_CLIENT_ID: str = ""
    NOTION_CLIENT_SECRET: str = ""
    NOTION_REDIRECT_URI: str = "http://localhost:5173/auth/notion/callback"
    NOTION_API_KEY: str = ""
    NOTION_DATABASE_ID: str = ""

    # Copilot LLM Configuration (Phase 3.5)
    COPILOT_LLM_PROVIDER: str = "gemini"  # 'gemini' or 'claude'
    GEMINI_API_KEY: str = ""
    # Google retires model versions; override without a code change when that happens
    GEMINI_MODEL: str = "gemini-flash-latest"
    ANTHROPIC_API_KEY: str = ""


    @field_validator("DATABASE_URL")
    @classmethod
    def _pin_postgres_driver(cls, v: str) -> str:
        """Hosts hand out postgres:// or postgresql:// URLs; newer SQLAlchemy maps those
        to psycopg v3, but we ship psycopg2."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix):]
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        """Accept a JSON list or a comma-separated string (hosting dashboards make JSON easy to mangle)."""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json
                return json.loads(s)
            return [o.strip() for o in s.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def _check_sandbox_production(self) -> "Settings":
        """Refuse to start with sandbox/simulated modes or insecure default secrets in production."""
        if self.ENVIRONMENT == "production":
            if "*" in self.ALLOWED_ORIGINS:
                raise RuntimeError(
                    "ALLOWED_ORIGINS must not contain '*' when ENVIRONMENT=production "
                    "(credentialed CORS would let any site act as the signed-in user)."
                )
            if self.DEV_SANDBOX_AUTH:
                raise RuntimeError(
                    "DEV_SANDBOX_AUTH=True is not allowed when ENVIRONMENT=production. "
                    "Set DEV_SANDBOX_AUTH=False in your production .env file."
                )
            if self.JIRA_SIMULATION_MODE:
                raise RuntimeError(
                    "JIRA_SIMULATION_MODE=True is not allowed when ENVIRONMENT=production. "
                    "Set JIRA_SIMULATION_MODE=False and configure live Jira credentials in production."
                )
            if self.NOTION_SIMULATION_MODE:
                raise RuntimeError(
                    "NOTION_SIMULATION_MODE=True is not allowed when ENVIRONMENT=production. "
                    "Set NOTION_SIMULATION_MODE=False and configure live Notion credentials in production."
                )

            # Production session secret check
            insecure_secret_defaults = {
                "",
                "super-secret-key-change-in-production-2026",
                "change-me-in-production-32-random-chars",
                "change-me",
            }
            if not self.SECRET_KEY or self.SECRET_KEY in insecure_secret_defaults:
                raise RuntimeError(
                    "Startup refused in production: SECRET_KEY is missing or using an insecure default. "
                    "Set a secure, unique random SECRET_KEY in your production .env file."
                )

            # Production JWT secret check
            insecure_jwt_defaults = {
                "",
                "pei-jwt-secret-key-production-2026",
                "change-me-in-production-32-random-chars",
                "change-me",
            }
            if not self.JWT_SECRET or self.JWT_SECRET in insecure_jwt_defaults:
                raise RuntimeError(
                    "Startup refused in production: JWT_SECRET is missing or using an insecure default. "
                    "Set a secure, unique random JWT_SECRET in your production .env file."
                )

            # Production token encryption key check
            insecure_token_defaults = {
                "",
                "jO6sB1JjIbyQVKkooyUsJrou4tx38pF8al656WmYkDg=",
                "your-fernet-encryption-key-here",
            }
            if not self.TOKEN_ENCRYPTION_KEY or self.TOKEN_ENCRYPTION_KEY in insecure_token_defaults:
                raise RuntimeError(
                    "Startup refused in production: TOKEN_ENCRYPTION_KEY is missing or using an insecure default. "
                    "Generate a valid 32-byte Fernet key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            # Any high-entropy value works (e.g. a host's "generate" button): TokenSecurity
            # derives its cipher key by hashing, so the Fernet format itself isn't required.
            if len(self.TOKEN_ENCRYPTION_KEY) < 32:
                raise RuntimeError(
                    "Startup refused in production: TOKEN_ENCRYPTION_KEY is too short (need 32+ random characters)."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

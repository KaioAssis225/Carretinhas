from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, carregada de variáveis de ambiente.

    Nenhum valor sensível possui default; em produção todos vêm do ambiente.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASSISCARRETAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AssisCarretas API"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    # Libera datas passadas e retirada antecipada apenas para simulações controladas.
    allow_test_rental_dates: bool = False

    api_v1_prefix: str = "/api/v1"

    # Origens permitidas para CORS, separadas por vírgula na variável de ambiente.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Sem prefixo ASSISCARRETAS_ por convenção de plataformas de deploy.
    # O default aponta para o PostgreSQL do docker-compose de desenvolvimento.
    database_url: str = Field(
        default="postgresql+psycopg://assiscarretas:dev-only-password@localhost:5432/assiscarretas",
        validation_alias="DATABASE_URL",
    )

    # --- Autenticação ---
    # Default utilizável apenas em desenvolvimento; validado abaixo.
    secret_key: str = "dev-only-secret-key-trocar-em-producao"  # noqa: S105 — validado abaixo
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    refresh_cookie_name: str = "assiscarretas_refresh"
    # Tentativas de login por IP+e-mail dentro da janela antes do 429
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    private_storage_dir: str = "/app/private-storage"
    max_inspection_photo_bytes: int = 8 * 1024 * 1024
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _usar_driver_psycopg(cls, value: object) -> object:
        """Adapta a URL PostgreSQL genérica fornecida por plataformas de deploy."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def _exigir_segredo_real_em_producao(self) -> "Settings":
        if self.environment == "production" and self.secret_key.startswith("dev-only-"):
            msg = "ASSISCARRETAS_SECRET_KEY precisa ser definido em produção."
            raise ValueError(msg)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        if self.environment != "local":
            return None
        # Permite que celulares na mesma rede privada acessem o Vite local.
        return (
            r"^http://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|"
            r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])"
            r"(?:\.\d{1,3}){2}):5173$"
        )

    @property
    def uses_s3_storage(self) -> bool:
        return all(
            (self.s3_endpoint, self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

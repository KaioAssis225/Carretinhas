from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
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

    @model_validator(mode="after")
    def _exigir_segredo_real_em_producao(self) -> "Settings":
        if self.environment == "production" and self.secret_key.startswith("dev-only-"):
            msg = "ASSISCARRETAS_SECRET_KEY precisa ser definido em produção."
            raise ValueError(msg)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

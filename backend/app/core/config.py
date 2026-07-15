from functools import lru_cache
from typing import Literal

from pydantic import Field
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
    cors_origins: str = "http://localhost:5173"

    # Sem prefixo ASSISCARRETAS_ por convenção de plataformas de deploy.
    # O default aponta para o PostgreSQL do docker-compose de desenvolvimento.
    database_url: str = Field(
        default="postgresql+psycopg://assiscarretas:dev-only-password@localhost:5432/assiscarretas",
        validation_alias="DATABASE_URL",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

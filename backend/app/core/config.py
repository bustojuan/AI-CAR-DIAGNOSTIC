from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    openai_api_key: SecretStr | None = None
    openai_model: str = Field(default="gpt-4.1-mini", min_length=1)
    llm_timeout_seconds: float = Field(default=30, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=3)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    max_request_bytes: int = Field(default=65536, ge=1024, le=1048576)
    max_history_messages: int = Field(default=20, ge=2, le=100)
    database_url: SecretStr | None = None
    db_pool_size: int = Field(default=5, ge=1, le=30)
    db_max_overflow: int = Field(default=5, ge=0, le=30)
    db_pool_timeout: float = Field(default=10, gt=0, le=60)
    db_connect_timeout: int = Field(default=5, ge=1, le=30)
    db_echo: bool = False
    embedding_dimensions: int = Field(default=1536, ge=1, le=2000)
    database_schema: str | None = Field(default=None, pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    rag_enabled: bool = True
    rag_allow_related_volkswagen: bool = False
    rag_query_expansion_enabled: bool = True
    rag_query_expansion_timeout_seconds: float = Field(default=4, gt=0, le=10)
    rag_admin_token: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = Field(default=32, ge=1, le=128)
    embedding_timeout_seconds: float = Field(default=30, gt=0, le=120)
    embedding_max_retries: int = Field(default=2, ge=0, le=3)
    rag_top_k: int = Field(default=4, ge=1, le=8)
    rag_rerank_candidates: int = Field(default=40, ge=8, le=64)
    rag_lexical_weight: float = Field(default=0.15, ge=0, le=0.3)
    rag_min_similarity: float = Field(default=0.35, ge=0, le=1)
    rag_timeout_seconds: float = Field(default=10, gt=0, le=60)
    document_max_bytes: int = Field(default=4194304, ge=1024, le=8388608)
    document_max_pages: int = Field(default=100, ge=1, le=500)
    document_max_characters: int = Field(default=500000, ge=1000, le=2000000)
    chunk_size: int = Field(default=1200, ge=300, le=1800)
    chunk_overlap: int = Field(default=150, ge=0, le=400)
    mcp_enabled: bool = False
    mcp_transport: Literal["stdio", "http"] = "stdio"
    automotive_provider: Literal["unavailable", "demo", "ebay", "ebay_sandbox"] = "unavailable"
    ebay_client_id: SecretStr | None = None
    ebay_client_secret: SecretStr | None = None
    ebay_sandbox_client_id: SecretStr | None = None
    ebay_sandbox_client_secret: SecretStr | None = None
    mcp_http_url: str = "http://127.0.0.1:8766/mcp"
    mcp_token: SecretStr | None = None
    mcp_timeout_seconds: float = Field(default=15, gt=0, le=60)
    mcp_provider_timeout_seconds: float = Field(default=5, gt=0, le=30)
    mcp_max_result_bytes: int = Field(default=32768, ge=2048, le=65536)
    parts_country: str = Field(default="ES", pattern=r"^[A-Z]{2}$")
    parts_currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def mcp_configuration(self):
        url = urlsplit(self.mcp_http_url)
        if (
            url.scheme != "http"
            or url.hostname not in ("127.0.0.1", "localhost", "::1")
            or url.path != "/mcp"
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("MCP_HTTP_URL must be a loopback HTTP /mcp endpoint")
        if self.mcp_token and len(self.mcp_token.get_secret_value()) < 24:
            raise ValueError("MCP_TOKEN must contain at least 24 characters")
        if self.mcp_enabled and self.mcp_transport == "http" and not self.mcp_token:
            raise ValueError("MCP HTTP requires MCP_TOKEN")
        return self

    @model_validator(mode="after")
    def rag_configuration(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.rag_admin_token and len(self.rag_admin_token.get_secret_value()) < 24:
            raise ValueError("RAG_ADMIN_TOKEN must contain at least 24 characters")
        return self

    @field_validator("database_url")
    @classmethod
    def postgres_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value:
            try:
                url = make_url(value.get_secret_value())
                if url.drivername != "postgresql+psycopg" or not url.database:
                    raise ValueError
            except Exception:
                raise ValueError("Use a postgresql+psycopg:// URL with a database name") from None
        return value

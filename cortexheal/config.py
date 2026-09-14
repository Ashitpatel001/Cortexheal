import os
from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "postgresql://cortexheal:cortexpassword@localhost:5432/cortexheal_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT: int = 30
    
    # API / Control Plane Configuration
    CORTEXHEAL_HOST: str = "0.0.0.0"
    CORTEXHEAL_PORT: int = 8000
    CORTEXHEAL_WORKERS: int = 4
    
    # Environment
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    
    # Authentication & Authorization
    ADMIN_TOKENS: str = "dev-admin-key"
    OPERATOR_TOKENS: str = "dev-operator-key"
    VIEWER_TOKENS: str = "dev-viewer-key"
    ALLOW_DEV_TOKENS: bool = False
    
    # Telemetry & Performance
    ENABLE_TELEMETRY: bool = True
    MAX_QUEUE_SIZE: int = 10000
    BATCH_SIZE: int = 100
    FLUSH_INTERVAL_MS: int = 500
    
    # Detection
    DETECTOR_VERSION: str = "1.0"
    POLICY_VERSION: str = "1.0"
    
    # Rate Limiting
    API_RATE_LIMIT_PER_MIN: int = 60
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    from pydantic import model_validator
    @model_validator(mode='after')
    def check_production_secrets(self) -> 'Settings':
        if self.ENVIRONMENT == "production":
            invalid_tokens = {"admin-key", "operator-key", "viewer-key", "dev-admin-key", "dev-operator-key", "dev-viewer-key"}
            if self.ADMIN_TOKENS in invalid_tokens or self.OPERATOR_TOKENS in invalid_tokens or self.VIEWER_TOKENS in invalid_tokens:
                raise ValueError("Default development authentication tokens cannot be used in production environment.")
            if self.DATABASE_URL == "postgresql://cortexheal:cortexpassword@localhost:5432/cortexheal_db":
                raise ValueError("Default database URL cannot be used in production environment.")
        return self

    def get_admin_tokens(self) -> List[str]:
        return [t.strip() for t in self.ADMIN_TOKENS.split(",")]

    def get_operator_tokens(self) -> List[str]:
        return [t.strip() for t in self.OPERATOR_TOKENS.split(",")]

    def get_viewer_tokens(self) -> List[str]:
        return [t.strip() for t in self.VIEWER_TOKENS.split(",")]

# Singleton settings instance
settings = Settings()
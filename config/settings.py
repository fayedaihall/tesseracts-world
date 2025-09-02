import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Tesseracts World API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str = "postgresql://user:password@localhost/tesseracts_world"
    
    # Redis for caching and queues
    redis_url: str = "redis://localhost:6379"
    
    # Provider API Keys (placeholder - these would be configured per deployment)
    uber_api_key: Optional[str] = None
    lyft_api_key: Optional[str] = None
    doordash_api_key: Optional[str] = None
    instacart_api_key: Optional[str] = None
    
    # Machine Learning settings
    route_optimization_model_path: str = "models/route_optimizer.pkl"
    demand_prediction_model_path: str = "models/demand_predictor.pkl"
    
    # Rate limiting
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    
    # Geolocation settings
    default_radius_km: float = 10.0
    max_radius_km: float = 50.0
    
    class Config:
        env_file = ".env"

settings = Settings()

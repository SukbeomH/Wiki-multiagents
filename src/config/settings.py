"""
설정 관리 클래스

환경 변수 및 설정 파일을 통합 관리합니다.
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    app_name: str = "AI Bootcamp Final"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API 설정
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # UI 설정
    ui_host: str = Field(default="0.0.0.0", env="UI_HOST")
    ui_port: int = Field(default=8501, env="UI_PORT")
    
    # 데이터베이스 설정
    database_url: str = Field(default="sqlite:///./data/app.db", env="DATABASE_URL")
    
    # 벡터 스토어 설정
    vector_store_path: str = Field(default="./data/vector_indices", env="VECTOR_STORE_PATH")
    faiss_index_path: str = Field(default="./data/vector_indices/faiss_index.bin", env="FAISS_INDEX_PATH")
    
    # 캐시 설정
    cache_dir: str = Field(default="./data/cache", env="CACHE_DIR")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # 로그 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # AI 모델 설정
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    
    # 검색 API 설정
    duckduckgo_api_key: Optional[str] = Field(default=None, env="DUCKDUCKGO_API_KEY")
    serpapi_key: Optional[str] = Field(default=None, env="SERPAPI_KEY")
    
    # 슬랙 설정
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 추가 환경 변수 무시


# 전역 설정 인스턴스
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """설정 인스턴스를 반환합니다."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_redis_config() -> Dict[str, Any]:
    """Redis 설정을 반환합니다 (호환성을 위해 유지)"""
    settings = get_settings()
    return {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
        "decode_responses": True
    }


def get_cache_config() -> Dict[str, Any]:
    """캐시 설정을 반환합니다"""
    settings = get_settings()
    return {
        "cache_dir": settings.cache_dir,
        "ttl": settings.cache_ttl
    }


def get_vector_store_config() -> Dict[str, Any]:
    """벡터 스토어 설정을 반환합니다"""
    settings = get_settings()
    return {
        "vector_store_path": settings.vector_store_path,
        "faiss_index_path": settings.faiss_index_path
    } 
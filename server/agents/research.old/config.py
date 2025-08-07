"""
Research Agent 성능 최적화 설정

성능 테스트 결과를 바탕으로 최적화된 설정값들을 정의합니다.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class PerformanceConfig:
    """성능 최적화 설정"""
    
    # 캐시 설정 (성능 테스트 결과 최적값)
    CACHE_MAX_SIZE: int = 128
    CACHE_TTL_SECONDS: int = 3600  # 1시간
    
    # 클라이언트 설정
    CLIENT_TIMEOUT: int = 10  # 초
    CLIENT_MAX_RETRIES: int = 3
    
    # 동시 실행 제한
    MAX_CONCURRENT_SEARCHES: int = 5
    
    # 성능 임계값
    MAX_SEARCH_TIME: float = 5.0  # 초
    MAX_MEMORY_INCREASE: float = 50.0  # MB
    MIN_CACHE_HIT_RATE: float = 0.3  # 30%
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """캐시 설정 반환"""
        return {
            'max_size': cls.CACHE_MAX_SIZE,
            'ttl_seconds': cls.CACHE_TTL_SECONDS,
            'log_level': cls.LOG_LEVEL
        }
    
    @classmethod
    def get_client_config(cls) -> Dict[str, Any]:
        """클라이언트 설정 반환"""
        return {
            'timeout': cls.CLIENT_TIMEOUT,
            'max_retries': cls.CLIENT_MAX_RETRIES,
            'log_level': cls.LOG_LEVEL
        }
    
    @classmethod
    def get_agent_config(cls) -> Dict[str, Any]:
        """Agent 설정 반환"""
        return {
            'log_level': cls.LOG_LEVEL,
            'max_concurrent_searches': cls.MAX_CONCURRENT_SEARCHES
        }


# 성능 최적화 설정 인스턴스
PERFORMANCE_CONFIG = PerformanceConfig() 
"""
Research Agent 모듈

성능 최적화된 웹 검색 기반 문서 수집 시스템
"""

from .agent import ResearchAgent
from .client import DuckDuckGoClient
from .cache import ResearchCache
from .config import PERFORMANCE_CONFIG

# 성능 최적화된 기본 인스턴스들
research_agent = ResearchAgent()
duckduckgo_client = DuckDuckGoClient(**PERFORMANCE_CONFIG.get_client_config())
research_cache = ResearchCache(**PERFORMANCE_CONFIG.get_cache_config())

__all__ = [
    'ResearchAgent',
    'DuckDuckGoClient', 
    'ResearchCache',
    'PERFORMANCE_CONFIG',
    'research_agent',
    'duckduckgo_client',
    'research_cache'
]
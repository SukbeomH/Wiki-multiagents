"""
Research Agent - DuckDuckGo Search 기반 웹 검색 RAG

개선된 모듈 구조를 사용한 Research Agent
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.schemas.agents import ResearchIn, ResearchOut
from src.agents.research.client import DuckDuckGoClient
from src.agents.research.cache import ResearchCache
from src.agents.research.config import PERFORMANCE_CONFIG


logger = logging.getLogger(__name__)


class ResearchAgent:
    """Research Agent - 웹 검색 기반 문서 수집 및 캐싱
    
    성능 최적화된 설정으로 안정적이고 빠른 문서 수집을 제공합니다.
    """
    
    def __init__(
        self,
        client: Optional[DuckDuckGoClient] = None,
        cache: Optional[ResearchCache] = None,
        log_level: str = "INFO",
        *,
        enable_cache: Optional[bool] = None,
    ):
        """
        Research Agent 초기화
        
        Args:
            client: DuckDuckGo 클라이언트 (기본값: 최적화된 설정으로 생성)
            cache: 캐시 시스템 (기본값: 최적화된 설정으로 생성)
            log_level: 로그 레벨
        """
        # 성능 최적화된 설정 적용
        config = PERFORMANCE_CONFIG.get_agent_config()
        self.log_level = log_level or config['log_level']
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # 클라이언트 초기화 (최적화된 설정 사용)
        if client is None:
            client_config = PERFORMANCE_CONFIG.get_client_config()
            self.client = DuckDuckGoClient(**client_config)
        else:
            self.client = client
        
        # 캐시 초기화 (최적화된 설정 사용)
        if cache is None:
            cache_config = PERFORMANCE_CONFIG.get_cache_config()
            # 테스트 호환: enable_cache=False면 캐시 비활성화
            if enable_cache is False:
                self.cache = None
            else:
                self.cache = ResearchCache(**cache_config)
        else:
            self.cache = cache

        # 외부에서 상태 확인 가능하도록 속성 유지
        self.enable_cache = self.cache is not None
        
        # 구조화된 초기화 로그
        self._log_structured(
            "research_agent_initialized",
            config={
                "enable_cache": True,
                "log_level": self.log_level,
                "client_type": "DuckDuckGoClient",
                "cache_type": "ResearchCache",
                "performance_optimized": True
            }
        )
    
    def _log_structured(self, event: str, **kwargs):
        """
        구조화된 JSON 로그 출력
        
        Args:
            event: 이벤트 이름
            **kwargs: 추가 로그 데이터
        """
        # Mock 객체나 직렬화할 수 없는 객체 처리
        safe_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(value, '__class__') and 'Mock' in value.__class__.__name__:
                safe_kwargs[key] = f"<{value.__class__.__name__}>"
            elif hasattr(value, 'get_stats') and callable(value.get_stats):
                try:
                    safe_kwargs[key] = value.get_stats()
                except:
                    safe_kwargs[key] = "<cache_stats_unavailable>"
            else:
                try:
                    # JSON 직렬화 테스트
                    json.dumps(value, ensure_ascii=False)
                    safe_kwargs[key] = value
                except (TypeError, ValueError):
                    safe_kwargs[key] = str(value)
        
        log_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **safe_kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def _convert_to_docs(self, search_results: List[Dict[str, Any]], query: str) -> tuple[List[str], List[Dict[str, Any]]]:
        """
        DuckDuckGo 검색 결과를 ResearchOut 형식으로 변환
        
        Args:
            search_results: DuckDuckGo 검색 결과
            query: 원본 검색 쿼리
            
        Returns:
            (docs, metadata) 튜플 - docs는 문서 내용 리스트, metadata는 메타데이터 리스트
        """
        docs = []
        metadata = []
        conversion_start = datetime.now()
        
        for i, result in enumerate(search_results):
            try:
                # DuckDuckGo 결과 구조: {title, href, body}
                title = result.get('title', '').strip()
                body = result.get('body', '').strip()
                url = result.get('href', '')
                
                # 문서 내용 (제목 + 본문)
                doc_content = f"{title}\n\n{body}".strip()
                docs.append(doc_content)
                
                # 메타데이터
                doc_metadata = {
                    'title': title,
                    'url': url,
                    'source': 'duckduckgo',
                    'search_query': query,
                    'search_rank': i + 1,
                    'timestamp': datetime.now().isoformat()
                }
                metadata.append(doc_metadata)
                
            except Exception as e:
                self._log_structured(
                    "document_conversion_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    result_index=i,
                    query=query
                )
                continue
        
        conversion_time = (datetime.now() - conversion_start).total_seconds()
        
        # 변환 완료 로그
        self._log_structured(
            "documents_converted",
            query=query,
            total_results=len(search_results),
            converted_docs=len(docs),
            conversion_time=conversion_time,
            success_rate=len(docs) / len(search_results) if search_results else 0
        )
        
        return docs, metadata
    
    async def search(self, input_data: ResearchIn) -> ResearchOut:
        """
        비동기 검색 수행 (메인 인터페이스)
        
        Args:
            input_data: 검색 입력 데이터
            
        Returns:
            검색 결과 출력 데이터
        """
        search_start = datetime.now()
        
        # 검색 시작 로그
        self._log_structured(
            "search_started",
            query=input_data.keyword,
            top_k=input_data.top_k,
            search_engines=input_data.search_engines,
            language=input_data.language,
            cache_enabled=input_data.cache_enabled
        )
        
        try:
            # 캐시 확인 (활성화된 경우)
            cache_hit = False
            cached_data = None
            cache_check_start = datetime.now()
            
            if self.cache and input_data.cache_enabled:
                cached_data = self.cache.get(
                    query=input_data.keyword,
                    region=getattr(input_data, 'region', 'wt-wt'),
                    top_k=input_data.top_k
                )
                
                cache_check_time = (datetime.now() - cache_check_start).total_seconds()
                
                if cached_data:
                    cache_hit = True
                    search_results, cached_metadata = cached_data
                    
                    self._log_structured(
                        "cache_hit",
                        query=input_data.keyword,
                        cache_check_time=cache_check_time,
                        cache_stats=self.cache.get_stats()
                    )
                else:
                    self._log_structured(
                        "cache_miss",
                        query=input_data.keyword,
                        cache_check_time=cache_check_time,
                        cache_stats=self.cache.get_stats()
                    )
            
            # 캐시 미스인 경우 실제 검색 수행
            if not cache_hit:
                api_call_start = datetime.now()
                
                # 동기 검색을 비동기로 실행
                loop = asyncio.get_event_loop()
                search_results = await loop.run_in_executor(
                    None, 
                    self.client.search, 
                    input_data.keyword,
                    getattr(input_data, 'region', 'wt-wt')
                )
                
                api_call_time = (datetime.now() - api_call_start).total_seconds()
                
                # API 호출 완료 로그
                self._log_structured(
                    "api_call_completed",
                    query=input_data.keyword,
                    api_call_time=api_call_time,
                    results_count=len(search_results)
                )
                
                # 캐시에 저장 (활성화된 경우)
                if self.cache and input_data.cache_enabled:
                    cache_store_start = datetime.now()
                    
                    # 임시 메타데이터 생성 (캐시 저장용)
                    temp_metadata = {
                        'cached_at': datetime.now().isoformat(),
                        'query': input_data.keyword,
                        'region': getattr(input_data, 'region', 'wt-wt'),
                        'top_k': input_data.top_k
                    }
                    
                    self.cache.set(
                        query=input_data.keyword,
                        results=search_results,
                        metadata=temp_metadata,
                        region=getattr(input_data, 'region', 'wt-wt'),
                        top_k=input_data.top_k
                    )
                    
                    cache_store_time = (datetime.now() - cache_store_start).total_seconds()
                    
                    self._log_structured(
                        "cache_stored",
                        query=input_data.keyword,
                        cache_store_time=cache_store_time
                    )
            
            # ResearchOut 형식으로 변환
            docs, metadata = self._convert_to_docs(search_results, input_data.keyword)
            
            # 검색 성공
            total_time = (datetime.now() - search_start).total_seconds()
            
            result = ResearchOut(
                docs=docs,
                metadata=metadata,
                cache_hit=cache_hit,
                processing_time=total_time
            )
            
            # 성공 로그 (상세 메트릭 포함)
            cache_stats = None
            if self.cache and hasattr(self.cache, 'get_stats'):
                try:
                    cache_stats = self.cache.get_stats()
                except:
                    cache_stats = "<cache_stats_unavailable>"
            
            cache_hit_rate = 0
            if cache_stats and isinstance(cache_stats, dict) and 'hit_rate' in cache_stats:
                cache_hit_rate = cache_stats['hit_rate']
            
            self._log_structured(
                "search_completed",
                query=input_data.keyword,
                total_time=total_time,
                docs_count=len(docs),
                cache_hit=cache_hit,
                cache_stats=cache_stats,
                performance_metrics={
                    "total_time": total_time,
                    "docs_per_second": len(docs) / total_time if total_time > 0 else 0,
                    "cache_hit_rate": cache_hit_rate
                }
            )
            
            return result
            
        except Exception as e:
            # 검색 실패
            total_time = (datetime.now() - search_start).total_seconds()
            
            # 오류 로그 (상세 정보 포함)
            cache_stats = None
            if self.cache and hasattr(self.cache, 'get_stats'):
                try:
                    cache_stats = self.cache.get_stats()
                except:
                    cache_stats = "<cache_stats_unavailable>"
            
            self._log_structured(
                "search_failed",
                query=input_data.keyword,
                error=str(e),
                error_type=type(e).__name__,
                total_time=total_time,
                cache_hit=cache_hit,
                cache_stats=cache_stats
            )
            
            return ResearchOut(
                docs=[],
                metadata=[{
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'search_engine': 'duckduckgo',
                    'region': getattr(input_data, 'region', 'wt-wt')
                }],
                cache_hit=False,
                processing_time=total_time
            )
    
    def clear_cache(self) -> None:
        """캐시 정리"""
        if self.cache:
            cache_stats_before = None
            cache_stats_after = None
            
            if hasattr(self.cache, 'get_stats'):
                try:
                    cache_stats_before = self.cache.get_stats()
                except:
                    cache_stats_before = "<cache_stats_unavailable>"
            
            self.cache.clear()
            
            if hasattr(self.cache, 'get_stats'):
                try:
                    cache_stats_after = self.cache.get_stats()
                except:
                    cache_stats_after = "<cache_stats_unavailable>"
            
            self._log_structured(
                "cache_cleared",
                cache_stats_before=cache_stats_before,
                cache_stats_after=cache_stats_after
            )
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        if self.cache:
            stats = None
            if hasattr(self.cache, 'get_stats'):
                try:
                    stats = self.cache.get_stats()
                except:
                    stats = {'error': '캐시 통계를 가져올 수 없습니다.'}
            
            # 캐시 정보 조회 로그
            self._log_structured(
                "cache_info_retrieved",
                cache_stats=stats
            )
            
            return stats
        else:
            self._log_structured(
                "cache_info_error",
                error="캐시가 비활성화되어 있습니다."
            )
            return {'error': '캐시가 비활성화되어 있습니다.'}
    
    def health_check(self) -> Dict[str, Any]:
        """Research Agent 상태 확인"""
        health_start = datetime.now()
        
        try:
            # 클라이언트 상태 확인
            client_health = self.client.health_check()
            
            # 캐시 상태 확인
            cache_health = self.cache.health_check() if self.cache else {'status': 'disabled'}
            
            health_time = (datetime.now() - health_start).total_seconds()
            
            health_status = {
                'status': 'healthy' if client_health['status'] == 'healthy' else 'unhealthy',
                'search_engine': 'duckduckgo',
                'api_key_required': False,
                'last_test': datetime.now().isoformat(),
                'health_check_time': health_time,
                'client': client_health,
                'cache': cache_health,
                'config': {
                    'enable_cache': self.cache is not None,
                    'log_level': self.log_level
                }
            }
            
            # 헬스 체크 로그
            self._log_structured(
                "health_check_completed",
                health_status=health_status['status'],
                health_check_time=health_time,
                client_status=client_health['status'],
                cache_status=cache_health['status']
            )
            
            return health_status
            
        except Exception as e:
            health_time = (datetime.now() - health_start).total_seconds()
            
            # 헬스 체크 실패 로그
            self._log_structured(
                "health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
                health_check_time=health_time
            )
            
            return {
                'status': 'unhealthy',
                'error': str(e),
                'error_type': type(e).__name__,
                'last_test': datetime.now().isoformat(),
                'health_check_time': health_time
            }


# Research Agent 인스턴스 (싱글톤 패턴)
research_agent = ResearchAgent()


async def research_search(input_data: ResearchIn) -> ResearchOut:
    """
    Research Agent 검색 함수 (외부 인터페이스)
    
    Args:
        input_data: 검색 입력 데이터
        
    Returns:
        검색 결과 출력 데이터
    """
    return await research_agent.search(input_data) 
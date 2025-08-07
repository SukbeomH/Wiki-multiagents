"""
DuckDuckGo Search API 클라이언트

ddgs 라이브러리를 사용한 DuckDuckGo 검색 API 클라이언트
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

logger = logging.getLogger(__name__)


class DuckDuckGoClient:
    """DuckDuckGo 검색 API 클라이언트
    
    성능 최적화된 설정으로 안정적이고 빠른 검색을 제공합니다.
    """
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, log_level: str = "INFO"):
        """
        DuckDuckGo 클라이언트 초기화
        
        Args:
            timeout: 요청 타임아웃 (초) - 성능 테스트 결과 최적값
            max_retries: 최대 재시도 횟수
            log_level: 로그 레벨
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_results_per_query = 10  # 기본값 추가
        self.retry_attempts = max_retries  # 호환성을 위한 별칭
        
        # 성능 최적화된 DDGS 설정
        self.ddgs = DDGS(
            timeout=timeout
        )
        
        # 성능 메트릭
        self.performance_metrics = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_retries': 0,
            'avg_response_time': 0.0,
            'last_search_time': None
        }
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 구조화된 초기화 로그
        self._log_structured(
            "client_initialized",
            timeout=timeout,
            max_retries=max_retries,
            log_level=log_level,
            search_engine="duckduckgo"
        )
    
    def _log_structured(self, event: str, **kwargs):
        """
        구조화된 JSON 로그 출력
        
        Args:
            event: 이벤트 이름
            **kwargs: 추가 로그 데이터
        """
        log_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def _update_performance_metrics(self, success: bool, response_time: float, retries: int = 0):
        """
        성능 메트릭 업데이트
        
        Args:
            success: 검색 성공 여부
            response_time: 응답 시간
            retries: 재시도 횟수
        """
        self.performance_metrics['total_searches'] += 1
        self.performance_metrics['total_retries'] += retries
        self.performance_metrics['last_search_time'] = datetime.now().isoformat()
        
        if success:
            self.performance_metrics['successful_searches'] += 1
        else:
            self.performance_metrics['failed_searches'] += 1
        
        # 평균 응답 시간 업데이트
        current_avg = self.performance_metrics['avg_response_time']
        total_searches = self.performance_metrics['total_searches']
        self.performance_metrics['avg_response_time'] = (
            (current_avg * (total_searches - 1) + response_time) / total_searches
        )
    
    def search(self, query: str, region: str = "wt-wt") -> List[Dict[str, Any]]:
        """
        DuckDuckGo 검색 수행
        
        Args:
            query: 검색 쿼리
            region: 검색 지역 코드 (기본값: wt-wt - 전 세계)
            
        Returns:
            검색 결과 리스트
        """
        search_start = datetime.now()
        
        # 검색 시작 로그
        self._log_structured(
            "search_started",
            query=query,
            region=region,
            timeout=self.timeout,
            max_results=self.max_results_per_query
        )
        
        for attempt in range(self.retry_attempts):
            try:
                attempt_start = datetime.now()
                
                self._log_structured(
                    "search_attempt",
                    query=query,
                    attempt=attempt + 1,
                    total_attempts=self.retry_attempts
                )
                
                results = self.ddgs.text(
                    query,  # 첫 번째 위치 인자
                    region=region,
                    safesearch="moderate",
                    timelimit=None,  # 시간 제한 없음
                    max_results=self.max_results_per_query
                )
                
                attempt_time = (datetime.now() - attempt_start).total_seconds()
                total_time = (datetime.now() - search_start).total_seconds()
                
                # 성공 로그
                self._log_structured(
                    "search_success",
                    query=query,
                    attempt=attempt + 1,
                    results_count=len(results),
                    attempt_time=attempt_time,
                    total_time=total_time,
                    performance_metrics=self.get_performance_metrics()
                )
                
                # 성능 메트릭 업데이트
                self._update_performance_metrics(True, total_time, attempt)
                
                return results
                
            except RatelimitException as e:
                attempt_time = (datetime.now() - attempt_start).total_seconds()
                
                self._log_structured(
                    "search_rate_limit",
                    query=query,
                    attempt=attempt + 1,
                    error=str(e),
                    attempt_time=attempt_time
                )
                
                if attempt < self.retry_attempts - 1:
                    # 지수 백오프 적용
                    wait_time = 2 ** attempt
                    self._log_structured(
                        "search_retry_wait",
                        query=query,
                        wait_time=wait_time,
                        next_attempt=attempt + 2
                    )
                    asyncio.sleep(wait_time)
                else:
                    # 최종 실패
                    total_time = (datetime.now() - search_start).total_seconds()
                    self._update_performance_metrics(False, total_time, attempt + 1)
                    raise
                    
            except TimeoutException as e:
                attempt_time = (datetime.now() - attempt_start).total_seconds()
                
                self._log_structured(
                    "search_timeout",
                    query=query,
                    attempt=attempt + 1,
                    error=str(e),
                    attempt_time=attempt_time
                )
                
                if attempt < self.retry_attempts - 1:
                    continue
                else:
                    # 최종 실패
                    total_time = (datetime.now() - search_start).total_seconds()
                    self._update_performance_metrics(False, total_time, attempt + 1)
                    raise
                    
            except DDGSException as e:
                attempt_time = (datetime.now() - attempt_start).total_seconds()
                
                self._log_structured(
                    "search_ddgs_error",
                    query=query,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt_time=attempt_time
                )
                
                if attempt < self.retry_attempts - 1:
                    continue
                else:
                    # 최종 실패
                    total_time = (datetime.now() - search_start).total_seconds()
                    self._update_performance_metrics(False, total_time, attempt + 1)
                    raise
                    
            except Exception as e:
                attempt_time = (datetime.now() - attempt_start).total_seconds()
                
                self._log_structured(
                    "search_unexpected_error",
                    query=query,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt_time=attempt_time
                )
                
                if attempt < self.retry_attempts - 1:
                    continue
                else:
                    # 최종 실패
                    total_time = (datetime.now() - search_start).total_seconds()
                    self._update_performance_metrics(False, total_time, attempt + 1)
                    raise
        
        # 모든 시도 실패시 빈 리스트 반환
        total_time = (datetime.now() - search_start).total_seconds()
        self._update_performance_metrics(False, total_time, self.retry_attempts)
        
        self._log_structured(
            "search_all_attempts_failed",
            query=query,
            total_attempts=self.retry_attempts,
            total_time=total_time
        )
        
        return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 반환"""
        total_searches = self.performance_metrics['total_searches']
        success_rate = (
            self.performance_metrics['successful_searches'] / total_searches 
            if total_searches > 0 else 0
        )
        
        return {
            'total_searches': total_searches,
            'successful_searches': self.performance_metrics['successful_searches'],
            'failed_searches': self.performance_metrics['failed_searches'],
            'success_rate': round(success_rate, 4),
            'total_retries': self.performance_metrics['total_retries'],
            'avg_response_time': round(self.performance_metrics['avg_response_time'], 6),
            'last_search_time': self.performance_metrics['last_search_time']
        }
    
    def health_check(self) -> Dict[str, Any]:
        """DuckDuckGo 클라이언트 상태 확인"""
        health_start = datetime.now()
        
        try:
            # 간단한 테스트 검색
            test_results = self.search("test", "wt-wt")
            
            health_time = (datetime.now() - health_start).total_seconds()
            
            health_status = {
                'status': 'healthy',
                'search_engine': 'duckduckgo',
                'api_key_required': False,
                'last_test': datetime.now().isoformat(),
                'health_check_time': health_time,
                'test_results_count': len(test_results),
                'performance_metrics': self.get_performance_metrics(),
                'config': {
                    'timeout': self.timeout,
                    'max_results_per_query': self.max_results_per_query,
                    'retry_attempts': self.retry_attempts,
                    'log_level': self.log_level
                }
            }
            
            # 헬스 체크 로그
            self._log_structured(
                "health_check_completed",
                health_status="healthy",
                health_check_time=health_time,
                test_results_count=len(test_results)
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


# 기본 클라이언트 인스턴스
duckduckgo_client = DuckDuckGoClient() 
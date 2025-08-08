"""
Research Agent 캐싱 시스템

cachetools 라이브러리를 사용한 고급 캐싱 기능
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from cachetools import LRUCache, TTLCache

logger = logging.getLogger(__name__)


class ResearchCache:
    """Research Agent 전용 캐시 시스템
    
    LRU 캐시와 TTL 캐시를 조합하여 성능과 메모리 효율성을 균형있게 제공합니다.
    """
    
    def __init__(
        self,
        max_size: int = 128,
        ttl_seconds: int = 3600,
        log_level: str = "INFO",
        *,
        enable_ttl: Optional[bool] = None,
    ):
        """
        Research Cache 초기화
        
        Args:
            max_size: LRU 캐시 최대 크기 (기본값: 128 - 성능 테스트 결과 최적값)
            ttl_seconds: TTL 캐시 만료 시간 (초)
            log_level: 로그 레벨
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_ttl = True if enable_ttl is None else bool(enable_ttl)
        
        # 성능 최적화된 캐시 설정
        self.lru_cache = LRUCache(maxsize=max_size)
        # 테스트 호환: enable_ttl=False인 경우 TTL 캐시 비활성화 허용
        if not self.enable_ttl:
            self.ttl_cache = None
        else:
            self.ttl_cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        
        # 통계 및 성능 메트릭
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'ttl_expirations': 0,
            'lru_evictions': 0
        }
        
        # 성능 메트릭
        self.performance_metrics = {
            'total_operations': 0,
            'avg_get_time': 0.0,
            'avg_set_time': 0.0,
            'peak_memory_usage': 0.0,
            'last_operation_time': None
        }
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 구조화된 초기화 로그
        self._log_structured(
            "cache_initialized",
            max_size=max_size,
            ttl_seconds=ttl_seconds,
            log_level=log_level,
            cache_type="ResearchCache"
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
    
    def _update_performance_metrics(self, operation: str, duration: float):
        """
        성능 메트릭 업데이트
        
        Args:
            operation: 작업 유형 ('get', 'set', 'delete')
            duration: 작업 소요 시간
        """
        self.performance_metrics['total_operations'] += 1
        self.performance_metrics['last_operation_time'] = datetime.now().isoformat()
        
        if operation == 'get':
            current_avg = self.performance_metrics['avg_get_time']
            total_gets = self.stats['hits'] + self.stats['misses']
            self.performance_metrics['avg_get_time'] = (
                (current_avg * (total_gets - 1) + duration) / total_gets
            )
        elif operation == 'set':
            current_avg = self.performance_metrics['avg_set_time']
            self.performance_metrics['avg_set_time'] = (
                (current_avg * (self.stats['sets'] - 1) + duration) / self.stats['sets']
            )
    
    def _generate_cache_key(self, query: str, region: str = "wt-wt", **kwargs) -> str:
        """
        캐시 키 생성
        
        Args:
            query: 검색 쿼리
            region: 검색 지역
            **kwargs: 추가 파라미터
            
        Returns:
            캐시 키 (해시)
        """
        # 캐시 키 구성 요소
        key_data = {
            'query': query.lower().strip(),
            'region': region.lower(),
            **kwargs
        }
        
        # JSON 직렬화 후 해시 생성
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def get(self, query: str, region: str = "wt-wt", **kwargs) -> Optional[Tuple[list, Dict[str, Any]]]:
        """
        캐시에서 데이터 조회
        
        Args:
            query: 검색 쿼리
            region: 검색 지역
            **kwargs: 추가 파라미터
            
        Returns:
            (검색 결과, 메타데이터) 튜플 또는 None
        """
        operation_start = datetime.now()
        cache_key = self._generate_cache_key(query, region, **kwargs)
        
        # TTL 캐시 우선 확인
        if self.ttl_cache and cache_key in self.ttl_cache:
            self.stats['hits'] += 1
            operation_time = (datetime.now() - operation_start).total_seconds()
            self._update_performance_metrics('get', operation_time)
            
            self._log_structured(
                "cache_ttl_hit",
                query=query,
                cache_key=cache_key,
                operation_time=operation_time,
                cache_stats=self.get_stats()
            )
            
            return self.ttl_cache[cache_key]
        
        # LRU 캐시 확인
        if cache_key in self.lru_cache:
            self.stats['hits'] += 1
            operation_time = (datetime.now() - operation_start).total_seconds()
            self._update_performance_metrics('get', operation_time)
            
            self._log_structured(
                "cache_lru_hit",
                query=query,
                cache_key=cache_key,
                operation_time=operation_time,
                cache_stats=self.get_stats()
            )
            
            return self.lru_cache[cache_key]
        
        # 캐시 미스
        self.stats['misses'] += 1
        operation_time = (datetime.now() - operation_start).total_seconds()
        self._update_performance_metrics('get', operation_time)
        
        self._log_structured(
            "cache_miss",
            query=query,
            cache_key=cache_key,
            operation_time=operation_time,
            cache_stats=self.get_stats()
        )
        
        return None
    
    def set(self, query: str, results: list, metadata: Dict[str, Any], 
            region: str = "wt-wt", **kwargs) -> None:
        """
        캐시에 데이터 저장
        
        Args:
            query: 검색 쿼리
            results: 검색 결과
            metadata: 메타데이터
            region: 검색 지역
            **kwargs: 추가 파라미터
        """
        operation_start = datetime.now()
        cache_key = self._generate_cache_key(query, region, **kwargs)
        
        # 캐시 데이터 구성
        cache_data = (results, metadata)
        
        # TTL 캐시에 저장 (활성화된 경우)
        if self.ttl_cache:
            # TTL 캐시가 가득 찬 경우 만료된 항목 추적
            if len(self.ttl_cache) >= self.max_size:
                self.stats['ttl_expirations'] += 1
            
            self.ttl_cache[cache_key] = cache_data
        
        # LRU 캐시에도 저장
        # LRU 캐시가 가득 찬 경우 eviction 추적
        if len(self.lru_cache) >= self.max_size:
            self.stats['lru_evictions'] += 1
        
        self.lru_cache[cache_key] = cache_data
        self.stats['sets'] += 1
        
        operation_time = (datetime.now() - operation_start).total_seconds()
        self._update_performance_metrics('set', operation_time)
        
        self._log_structured(
            "cache_set",
            query=query,
            cache_key=cache_key,
            operation_time=operation_time,
            results_count=len(results),
            cache_stats=self.get_stats()
        )
    
    def delete(self, query: str, region: str = "wt-wt", **kwargs) -> bool:
        """
        캐시에서 데이터 삭제
        
        Args:
            query: 검색 쿼리
            region: 검색 지역
            **kwargs: 추가 파라미터
            
        Returns:
            삭제 성공 여부
        """
        operation_start = datetime.now()
        cache_key = self._generate_cache_key(query, region, **kwargs)
        deleted = False
        
        # TTL 캐시에서 삭제
        if self.ttl_cache and cache_key in self.ttl_cache:
            del self.ttl_cache[cache_key]
            deleted = True
        
        # LRU 캐시에서 삭제
        if cache_key in self.lru_cache:
            del self.lru_cache[cache_key]
            deleted = True
        
        if deleted:
            self.stats['deletes'] += 1
            operation_time = (datetime.now() - operation_start).total_seconds()
            
            self._log_structured(
                "cache_delete",
                query=query,
                cache_key=cache_key,
                operation_time=operation_time,
                cache_stats=self.get_stats()
            )
        
        return deleted
    
    def clear(self) -> None:
        """모든 캐시 정리"""
        operation_start = datetime.now()
        
        # 정리 전 통계
        stats_before = self.get_stats()
        
        self.lru_cache.clear()
        if self.ttl_cache:
            self.ttl_cache.clear()
        
        # 통계 초기화
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'ttl_expirations': 0,
            'lru_evictions': 0
        }
        
        # 성능 메트릭 초기화
        self.performance_metrics = {
            'total_operations': 0,
            'avg_get_time': 0.0,
            'avg_set_time': 0.0,
            'peak_memory_usage': 0,
            'last_operation_time': None
        }
        
        operation_time = (datetime.now() - operation_start).total_seconds()
        
        self._log_structured(
            "cache_cleared",
            operation_time=operation_time,
            stats_before=stats_before,
            stats_after=self.get_stats()
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        # 메모리 사용량 추정 (대략적)
        estimated_memory = (
            len(self.lru_cache) * 1024 +  # 각 항목 약 1KB 추정
            (len(self.ttl_cache) if self.ttl_cache else 0) * 1024
        )
        
        # 성능 메트릭 포함
        stats = {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'ttl_expirations': self.stats['ttl_expirations'],
            'lru_evictions': self.stats['lru_evictions'],
            'hit_rate': round(hit_rate, 4),
            'total_requests': total_requests,
            'lru_cache_size': len(self.lru_cache),
            'ttl_cache_size': len(self.ttl_cache) if self.ttl_cache else 0,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'enable_ttl': self.enable_ttl,
            'performance': {
                'total_operations': self.performance_metrics['total_operations'],
                'avg_get_time': round(self.performance_metrics['avg_get_time'], 6),
                'avg_set_time': round(self.performance_metrics['avg_set_time'], 6),
                'estimated_memory_kb': estimated_memory,
                'last_operation_time': self.performance_metrics['last_operation_time']
            }
        }
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """캐시 시스템 상태 확인"""
        health_start = datetime.now()
        
        try:
            stats = self.get_stats()
            
            # 캐시 상태 평가
            cache_health = 'healthy'
            warnings = []
            
            # 히트율이 너무 낮은 경우 경고
            if stats['total_requests'] > 10 and stats['hit_rate'] < 0.1:
                cache_health = 'warning'
                warnings.append(f"낮은 캐시 히트율: {stats['hit_rate']:.2%}")
            
            # 캐시가 거의 가득 찬 경우 경고
            if stats['lru_cache_size'] > self.max_size * 0.9:
                cache_health = 'warning'
                warnings.append(f"캐시 용량 부족: {stats['lru_cache_size']}/{self.max_size}")
            
            # 평균 응답 시간이 너무 긴 경우 경고
            if stats['performance']['avg_get_time'] > 0.1:  # 100ms 이상
                cache_health = 'warning'
                warnings.append(f"느린 캐시 응답: {stats['performance']['avg_get_time']:.3f}s")
            
            health_time = (datetime.now() - health_start).total_seconds()
            
            health_status = {
                'status': cache_health,
                'cache_type': 'research_cache',
                'last_check': datetime.now().isoformat(),
                'health_check_time': health_time,
                'stats': stats,
                'warnings': warnings,
                'config': {
                    'max_size': self.max_size,
                    'ttl_seconds': self.ttl_seconds,
                    'enable_ttl': self.enable_ttl,
                    'log_level': self.logger.level # 로거 레벨 사용
                }
            }
            
            # 헬스 체크 로그
            self._log_structured(
                "cache_health_check",
                health_status=cache_health,
                health_check_time=health_time,
                warnings=warnings,
                hit_rate=stats['hit_rate'],
                cache_utilization=stats['lru_cache_size'] / self.max_size
            )
            
            return health_status
            
        except Exception as e:
            health_time = (datetime.now() - health_start).total_seconds()
            
            # 헬스 체크 실패 로그
            self._log_structured(
                "cache_health_check_failed",
                error=str(e),
                error_type=type(e).__name__,
                health_check_time=health_time
            )
            
            return {
                'status': 'unhealthy',
                'error': str(e),
                'error_type': type(e).__name__,
                'last_check': datetime.now().isoformat(),
                'health_check_time': health_time
            }


# 기본 캐시 인스턴스
research_cache = ResearchCache() 
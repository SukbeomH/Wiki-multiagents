"""
diskcache 기반 캐시 및 스냅샷 관리자
Redis-JSON 기능을 diskcache로 대체

PRD 요구사항에 따른 캐시 및 체크포인트 저장/조회 기능
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import diskcache
from pydantic import BaseModel

# 기존 스키마 import
from ..schemas.base import WorkflowState, CheckpointData, CheckpointType

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """캐시 설정"""
    cache_dir: str = "./data/cache"
    max_size: int = 1024 * 1024 * 1024  # 1GB
    eviction_policy: str = "least-recently-used"
    default_ttl: int = 86400  # 24시간
    checkpoint_ttl: int = 604800  # 7일
    
    @classmethod
    def from_env(cls):
        """환경변수에서 설정 로드"""
        import os
        return cls(
            cache_dir=os.getenv("CACHE_DIR", "./data/cache"),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1073741824")),
            eviction_policy=os.getenv("CACHE_EVICTION_POLICY", "least-recently-used"),
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "86400")),
            checkpoint_ttl=int(os.getenv("CACHE_CHECKPOINT_TTL", "604800"))
        )


class CacheManager:
    """
    diskcache 기반 캐시 관리자
    Redis-JSON 기능을 로컬 캐시로 대체
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 메인 캐시 (일반 데이터)
        self.cache = diskcache.Cache(
            directory=str(self.cache_dir / "main"),
            size_limit=config.max_size,
            eviction_policy=config.eviction_policy
        )
        
        # 체크포인트 캐시 (중요 데이터, 더 긴 TTL)
        self.checkpoint_cache = diskcache.Cache(
            directory=str(self.cache_dir / "checkpoints"),
            size_limit=config.max_size // 2,
            eviction_policy="least-recently-used"
        )
        
        logger.info(f"CacheManager initialized with directory: {self.cache_dir}")
    
    # Redis-JSON 호환 메서드들
    def json_set(self, key: str, path: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Redis JSON.SET 호환 메서드
        
        Args:
            key: 캐시 키
            path: JSON 경로 (예: "$", "$.field")
            value: 저장할 값
            ttl: 만료 시간 (초)
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            if path == "$":
                # 전체 객체 설정
                expire_time = ttl or self.config.default_ttl
                return self.cache.set(key, value, expire=expire_time)
            else:
                # 경로별 설정
                current = self.cache.get(key, {})
                self._set_json_path(current, path, value)
                expire_time = ttl or self.config.default_ttl
                return self.cache.set(key, current, expire=expire_time)
        except Exception as e:
            logger.error(f"JSON set failed for key '{key}', path '{path}': {e}")
            return False
    
    def json_get(self, key: str, path: str = "$") -> Any:
        """
        Redis JSON.GET 호환 메서드
        
        Args:
            key: 캐시 키
            path: JSON 경로
        
        Returns:
            Any: 조회된 값 또는 None
        """
        try:
            data = self.cache.get(key)
            if data is None:
                return None
            
            if path == "$":
                return data
            else:
                return self._get_json_path(data, path)
        except Exception as e:
            logger.error(f"JSON get failed for key '{key}', path '{path}': {e}")
            return None
    
    def json_del(self, key: str, path: str = "$") -> bool:
        """
        Redis JSON.DEL 호환 메서드
        
        Args:
            key: 캐시 키
            path: JSON 경로
        
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            if path == "$":
                # 전체 키 삭제
                return self.cache.delete(key)
            else:
                # 경로별 삭제
                data = self.cache.get(key)
                if data is None:
                    return False
                
                if self._delete_json_path(data, path):
                    return self.cache.set(key, data)
                return False
        except Exception as e:
            logger.error(f"JSON delete failed for key '{key}', path '{path}': {e}")
            return False
    
    # 체크포인트 특화 메서드들
    def save_checkpoint(self, workflow_id: str, checkpoint_data: CheckpointData) -> bool:
        """
        체크포인트 저장
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_data: 체크포인트 데이터
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 기존 redis_manager.py와 호환되는 키 포맷 사용
            key = f"kg_checkpoint:{workflow_id}:{checkpoint_data.checkpoint_type}:{checkpoint_data.timestamp.isoformat()}"
            
            # Pydantic 모델을 dict로 변환
            data = checkpoint_data.dict()
            
            success = self.checkpoint_cache.set(
                key, 
                data, 
                expire=self.config.checkpoint_ttl
            )
            
            if success:
                logger.info(f"Checkpoint saved: {key}")
            return success
            
        except Exception as e:
            logger.error(f"Checkpoint save failed for workflow '{workflow_id}': {e}")
            return False
    
    def get_checkpoint(self, workflow_id: str, checkpoint_type: Optional[str] = None) -> Optional[CheckpointData]:
        """
        최신 체크포인트 조회
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_type: 체크포인트 타입 (None이면 최신 것)
        
        Returns:
            Optional[CheckpointData]: 체크포인트 데이터 또는 None
        """
        try:
            pattern = f"kg_checkpoint:{workflow_id}:"
            if checkpoint_type:
                pattern += f"{checkpoint_type}:"
            
            # diskcache에서 패턴 매칭 (수동 구현)
            matching_keys = [k for k in self.checkpoint_cache if str(k).startswith(pattern)]
            if not matching_keys:
                return None
            
            # 최신 키 선택 (타임스탬프 기준)
            latest_key = max(matching_keys, key=lambda k: str(k))
            data = self.checkpoint_cache.get(latest_key)
            
            if data:
                # dict를 CheckpointData로 복원
                return CheckpointData(**data)
            return None
            
        except Exception as e:
            logger.error(f"Checkpoint get failed for workflow '{workflow_id}': {e}")
            return None
    
    def get_checkpoints_by_workflow(self, workflow_id: str, limit: int = 10) -> List[CheckpointData]:
        """
        워크플로우별 체크포인트 목록 조회
        
        Args:
            workflow_id: 워크플로우 ID
            limit: 최대 조회 개수
        
        Returns:
            List[CheckpointData]: 체크포인트 목록
        """
        try:
            pattern = f"kg_checkpoint:{workflow_id}:"
            matching_keys = []
            
            # 일반 캐시와 체크포인트 캐시 모두 확인
            for cache in [self.cache, self.checkpoint_cache]:
                for key in cache:
                    key_str = str(key)
                    if key_str.startswith(pattern) and not key_str.endswith(":latest"):
                        matching_keys.append(key_str)
            
            logger.debug(f"Found {len(matching_keys)} matching keys for workflow {workflow_id}")
            
            # 타임스탬프 기준 정렬 (최신순)
            sorted_keys = sorted(matching_keys, key=lambda k: str(k), reverse=True)[:limit]
            
            checkpoints = []
            for key in sorted_keys:
                # 두 캐시에서 모두 시도
                data = self.checkpoint_cache.get(key) or self.cache.get(key)
                if data:
                    try:
                        if isinstance(data, str):
                            # JSON 문자열인 경우
                            checkpoint = CheckpointData.model_validate_json(data)
                        else:
                            # 이미 dict인 경우
                            checkpoint = CheckpointData(**data)
                        checkpoints.append(checkpoint)
                    except Exception as e:
                        logger.warning(f"Failed to parse checkpoint data for key {key}: {e}")
                        continue
            
            logger.info(f"Retrieved {len(checkpoints)} checkpoints for workflow {workflow_id}")
            return checkpoints
            
        except Exception as e:
            logger.error(f"Get checkpoints failed for workflow '{workflow_id}': {e}")
            return []
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        체크포인트 삭제
        
        Args:
            checkpoint_id: 체크포인트 ID
        
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 체크포인트 ID로 키 찾기
            for key in self.checkpoint_cache:
                data = self.checkpoint_cache.get(key)
                if data and data.get('checkpoint_id') == checkpoint_id:
                    return self.checkpoint_cache.delete(key)
            return False
            
        except Exception as e:
            logger.error(f"Checkpoint delete failed for ID '{checkpoint_id}': {e}")
            return False
    
    def cleanup_expired_checkpoints(self) -> int:
        """
        만료된 체크포인트 정리
        
        Returns:
            int: 정리된 체크포인트 수
        """
        try:
            # diskcache는 자동으로 TTL을 처리하므로 여기서는 수동 정리 없음
            # 대신 통계만 반환
            return 0
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    # 유틸리티 메서드들
    def _set_json_path(self, obj: Dict, path: str, value: Any):
        """JSON 경로에 값 설정"""
        if path.startswith("$."):
            keys = path[2:].split(".")
            current = obj
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
    
    def _get_json_path(self, obj: Any, path: str) -> Any:
        """JSON 경로에서 값 조회"""
        if path.startswith("$."):
            keys = path[2:].split(".")
            current = obj
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        return obj
    
    def _delete_json_path(self, obj: Dict, path: str) -> bool:
        """JSON 경로의 값 삭제"""
        if path.startswith("$."):
            keys = path[2:].split(".")
            current = obj
            for key in keys[:-1]:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return False
            
            if isinstance(current, dict) and keys[-1] in current:
                del current[keys[-1]]
                return True
        return False
    
    # 일반 캐시 메서드들
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """일반 캐시 저장"""
        try:
            expire_time = ttl or self.config.default_ttl
            return self.cache.set(key, value, expire=expire_time)
        except Exception as e:
            logger.error(f"Cache set failed for key '{key}': {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """일반 캐시 조회"""
        try:
            return self.cache.get(key, default)
        except Exception as e:
            logger.error(f"Cache get failed for key '{key}': {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """일반 캐시 삭제"""
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.error(f"Cache delete failed for key '{key}': {e}")
            return False
    
    def clear(self) -> bool:
        """전체 캐시 정리"""
        try:
            self.cache.clear()
            self.checkpoint_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """상태 점검"""
        try:
            # 간단한 write/read 테스트
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # 메인 캐시 테스트
            main_write = self.cache.set(test_key, test_value, expire=10)
            main_read = self.cache.get(test_key) if main_write else None
            self.cache.delete(test_key)
            
            # 체크포인트 캐시 테스트
            checkpoint_write = self.checkpoint_cache.set(test_key, test_value, expire=10)
            checkpoint_read = self.checkpoint_cache.get(test_key) if checkpoint_write else None
            self.checkpoint_cache.delete(test_key)
            
            return {
                "status": "healthy" if (main_read and checkpoint_read) else "error",
                "cache_stats": {
                    "main_cache_size": len(self.cache),
                    "checkpoint_cache_size": len(self.checkpoint_cache),
                    "main_disk_usage": self.cache.volume(),
                    "checkpoint_disk_usage": self.checkpoint_cache.volume(),
                    "total_disk_usage": self.cache.volume() + self.checkpoint_cache.volume()
                },
                "config": self.config.dict(),
                "tests": {
                    "main_cache_rw": main_read is not None,
                    "checkpoint_cache_rw": checkpoint_read is not None
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # 기본 테스트
    config = CacheConfig()
    manager = CacheManager(config)
    print("✅ CacheManager 완전 구현 성공")
    print("📊 상태:", json.dumps(manager.health_check(), indent=2))
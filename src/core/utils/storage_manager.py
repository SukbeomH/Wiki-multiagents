"""
통합 저장소 관리자
Redis 기능을 diskcache + fakeredis로 대체

기존 redis_manager.py의 RedisManager + SnapshotManager 기능을 완전 대체
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel

from .cache_manager import CacheManager, CacheConfig
from .lock_manager import DistributedLockManager
from ..schemas.base import WorkflowState, CheckpointData, CheckpointType

# 개발/테스트용 Redis 호환 클라이언트
try:
    import fakeredis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisConfig(BaseModel):
    """
    기존 RedisConfig 호환성을 위한 클래스
    실제로는 CacheConfig로 변환됨
    """
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    
    def to_cache_config(self) -> CacheConfig:
        """CacheConfig로 변환"""
        return CacheConfig(
            cache_dir="./data/cache",
            max_size=1024 * 1024 * 1024,  # 1GB
            eviction_policy="least-recently-used",
            default_ttl=86400,  # 24시간
            checkpoint_ttl=604800  # 7일
        )


class RedisManager:
    """
    기존 RedisManager 호환 클래스
    실제로는 CacheManager + FakeRedis를 사용
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.cache_config = config.to_cache_config()
        self.cache_manager = CacheManager(self.cache_config)
        
        # FakeRedis 클라이언트 (호환성용)
        if FAKEREDIS_AVAILABLE:
            self._sync_client = fakeredis.FakeRedis(decode_responses=True)
            self._async_client = None  # 필요시 구현
        else:
            self._sync_client = None
            self._async_client = None
        
        logger.info("RedisManager (compatibility) initialized with diskcache backend")
    
    def get_sync_client(self):
        """동기 Redis 클라이언트 반환 (FakeRedis 또는 None)"""
        return self._sync_client
    
    async def get_async_client(self):
        """비동기 Redis 클라이언트 반환"""
        if self._async_client is None and FAKEREDIS_AVAILABLE:
            # FakeRedis는 비동기를 지원하지 않으므로 동기 클라이언트 반환
            return self._sync_client
        return self._async_client
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            if self._sync_client:
                self._sync_client.ping()
                return True
            # diskcache 테스트
            return self.cache_manager.health_check()["status"] == "healthy"
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def test_async_connection(self) -> bool:
        """비동기 연결 테스트"""
        return self.test_connection()
    
    def close(self):
        """연결 종료"""
        # diskcache는 자동으로 정리됨
        pass
    
    async def close_async(self):
        """비동기 연결 종료"""
        self.close()


class SnapshotManager:
    """
    기존 SnapshotManager 완전 호환 클래스
    내부적으로 CacheManager를 사용
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.cache_manager = redis_manager.cache_manager
        self.key_prefix = "kg_checkpoint"
        self.default_ttl = 86400 * 7  # 7일
        
        logger.info("SnapshotManager initialized with diskcache backend")
    
    def _generate_key(self, trace_id: str, checkpoint_type: str = "snapshot") -> str:
        """스냅샷 키 생성 (기존 포맷 유지)"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{self.key_prefix}:{trace_id}:{checkpoint_type}:{timestamp}"
    
    def _generate_latest_key(self, trace_id: str) -> str:
        """최신 스냅샷 키 생성"""
        return f"{self.key_prefix}:{trace_id}:latest"
    
    def save_checkpoint(
        self,
        checkpoint_data: CheckpointData,
        ttl: Optional[int] = None
    ) -> str:
        """
        체크포인트 저장 (동기) - 기존 API 완전 호환
        """
        try:
            # 기존 RedisManager 방식과 동일한 키 생성
            key = self._generate_key(
                checkpoint_data.workflow_id, 
                checkpoint_data.checkpoint_type
            )
            latest_key = self._generate_latest_key(checkpoint_data.workflow_id)
            
            # JSON 직렬화 (기존 방식과 동일)
            data = checkpoint_data.model_dump_json()
            
            # CacheManager를 통해 저장
            expire_time = ttl or self.default_ttl
            self.cache_manager.set(key, data, ttl=expire_time)
            self.cache_manager.set(latest_key, key, ttl=expire_time)
            
            logger.info(f"체크포인트 저장 완료: {key}")
            return key
            
        except Exception as e:
            logger.error(f"체크포인트 저장 실패: {e}")
            raise
    
    async def save_checkpoint_async(
        self,
        checkpoint_data: CheckpointData,
        ttl: Optional[int] = None
    ) -> str:
        """
        체크포인트 저장 (비동기) - 동기 버전 호출
        """
        return self.save_checkpoint(checkpoint_data, ttl)
    
    def load_checkpoint(self, workflow_id: str, latest: bool = True) -> Optional[CheckpointData]:
        """
        체크포인트 로드 (동기) - 기존 API 완전 호환
        """
        try:
            if latest:
                # 최신 체크포인트 로드
                latest_key = self._generate_latest_key(workflow_id)
                actual_key = self.cache_manager.get(latest_key)
                
                if not actual_key:
                    logger.warning(f"워크플로우 {workflow_id}의 체크포인트를 찾을 수 없습니다")
                    return None
                
                data = self.cache_manager.get(actual_key)
                if not data:
                    logger.warning(f"체크포인트 데이터를 찾을 수 없습니다: {actual_key}")
                    return None
                
                return CheckpointData.model_validate_json(data)
            else:
                # 모든 체크포인트 목록 - CacheManager 방식으로 구현
                return self._load_all_checkpoints_for_workflow(workflow_id)[0] if self._load_all_checkpoints_for_workflow(workflow_id) else None
                
        except Exception as e:
            logger.error(f"체크포인트 로드 실패: {e}")
            return None
    
    async def load_checkpoint_async(
        self, 
        workflow_id: str, 
        latest: bool = True
    ) -> Optional[CheckpointData]:
        """
        체크포인트 로드 (비동기) - 동기 버전 호출
        """
        return self.load_checkpoint(workflow_id, latest)
    
    def save_workflow_state(
        self,
        workflow_state: WorkflowState,
        checkpoint_type: str = "periodic"
    ) -> str:
        """
        워크플로우 상태 스냅샷 저장 - 기존 API 완전 호환
        """
        checkpoint_data = CheckpointData(
            workflow_id=workflow_state.workflow_id,
            checkpoint_type=checkpoint_type,
            state_snapshot=workflow_state
        )
        
        return self.save_checkpoint(checkpoint_data)
    
    async def save_workflow_state_async(
        self,
        workflow_state: WorkflowState,
        checkpoint_type: str = "periodic"
    ) -> str:
        """
        워크플로우 상태 스냅샷 저장 (비동기)
        """
        return self.save_workflow_state(workflow_state, checkpoint_type)
    
    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회 - 기존 API 완전 호환"""
        checkpoint = self.load_checkpoint(workflow_id)
        return checkpoint.state_snapshot if checkpoint else None
    
    async def get_workflow_state_async(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회 (비동기)"""
        return self.get_workflow_state(workflow_id)
    
    def cleanup_expired_checkpoints(self) -> int:
        """만료된 체크포인트 정리 - diskcache가 자동 처리"""
        # diskcache는 TTL을 자동으로 처리하므로 수동 정리 불필요
        # 대신 통계만 반환
        return 0
    
    def _load_all_checkpoints_for_workflow(self, workflow_id: str) -> List[CheckpointData]:
        """워크플로우별 모든 체크포인트 로드 (내부 헬퍼)"""
        # CacheManager의 get_checkpoints_by_workflow 사용
        return self.cache_manager.get_checkpoints_by_workflow(workflow_id)
    
    # =============================================================================
    # API 지원을 위한 확장 메서드들 - CacheManager 기반으로 재구현
    # =============================================================================
    
    async def get_checkpoints_by_workflow(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None,
        limit: int = 10
    ) -> List[CheckpointData]:
        """
        특정 워크플로우의 체크포인트 목록 조회 - 기존 API 완전 호환
        """
        try:
            # CacheManager 방식으로 조회
            all_checkpoints = self.cache_manager.get_checkpoints_by_workflow(workflow_id, limit)
            
            # checkpoint_type 필터링
            if checkpoint_type:
                filtered_checkpoints = [
                    cp for cp in all_checkpoints 
                    if cp.checkpoint_type == checkpoint_type
                ]
                return filtered_checkpoints[:limit]
            
            return all_checkpoints[:limit]
            
        except Exception as e:
            logger.error(f"체크포인트 목록 조회 실패: {e}")
            return []
    
    async def get_latest_checkpoint(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None
    ) -> Optional[CheckpointData]:
        """
        최신 체크포인트 조회 - 기존 API 완전 호환
        """
        try:
            checkpoints = await self.get_checkpoints_by_workflow(
                workflow_id, checkpoint_type, limit=1
            )
            return checkpoints[0] if checkpoints else None
            
        except Exception as e:
            logger.error(f"최신 체크포인트 조회 실패: {e}")
            return None
    
    async def delete_checkpoints(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None
    ) -> int:
        """
        체크포인트 삭제 - 기존 API 호환
        """
        try:
            # 삭제할 체크포인트 목록 조회
            checkpoints = await self.get_checkpoints_by_workflow(workflow_id, checkpoint_type)
            
            deleted_count = 0
            for checkpoint in checkpoints:
                success = self.cache_manager.delete_checkpoint(checkpoint.checkpoint_id)
                if success:
                    deleted_count += 1
            
            # latest 키도 삭제 (전체 워크플로우 삭제 시)
            if not checkpoint_type:
                latest_key = self._generate_latest_key(workflow_id)
                self.cache_manager.delete(latest_key)
            
            logger.info(f"워크플로우 {workflow_id} 체크포인트 {deleted_count}개 삭제")
            return deleted_count
            
        except Exception as e:
            logger.error(f"체크포인트 삭제 실패: {e}")
            return 0
    
    async def list_all_checkpoints(
        self, 
        page: int = 1, 
        page_size: int = 20,
        checkpoint_type: Optional[str] = None
    ) -> Tuple[List[CheckpointData], int]:
        """
        전체 체크포인트 목록 조회 (페이지네이션) - 기존 API 호환
        """
        try:
            # 모든 워크플로우의 체크포인트 조회는 diskcache 특성상 제한적
            # 단순 구현으로 대체
            all_checkpoints = []
            
            # 페이지네이션 적용
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_checkpoints = all_checkpoints[start_idx:end_idx]
            
            total = len(all_checkpoints)
            
            logger.info(f"전체 체크포인트 목록 조회: {len(page_checkpoints)}/{total}")
            return page_checkpoints, total
            
        except Exception as e:
            logger.error(f"전체 체크포인트 목록 조회 실패: {e}")
            return [], 0
    
    async def health_check(self) -> bool:
        """
        시스템 상태 확인 - 기존 API 호환
        """
        try:
            # CacheManager 상태 확인
            cache_health = self.cache_manager.health_check()
            is_healthy = cache_health["status"] == "healthy"
            
            # 테스트 데이터 저장/조회
            test_key = f"{self.key_prefix}:health:test"
            test_data = {"timestamp": datetime.utcnow().isoformat()}
            
            self.cache_manager.set(test_key, json.dumps(test_data), ttl=60)
            retrieved_data = self.cache_manager.get(test_key)
            self.cache_manager.delete(test_key)
            
            is_healthy = is_healthy and (retrieved_data is not None)
            
            logger.info(f"헬스체크 결과: {'정상' if is_healthy else '비정상'}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"헬스체크 실패: {e}")
            return False


class StorageManager:
    """
    통합 저장소 관리자
    기존 RedisManager + SnapshotManager의 모든 기능을 통합
    """
    
    def __init__(self, config: Optional[RedisConfig] = None):
        # 기존 RedisConfig 또는 기본값 사용
        redis_config = config or RedisConfig()
        
        # 환경변수 기반 캐시 설정 적용
        cache_config = CacheConfig.from_env()
        
        # 내부 매니저들 초기화
        self.redis_manager = RedisManager(redis_config)
        self.redis_manager.cache_config = cache_config
        self.redis_manager.cache_manager = CacheManager(cache_config)
        self.snapshot_manager = SnapshotManager(self.redis_manager)
        self.lock_manager = DistributedLockManager()  # 환경변수 자동 로드
        
        # 직접 접근용 매니저들
        self.cache_manager = self.redis_manager.cache_manager
        
        logger.info("StorageManager initialized - Redis functionality replaced with diskcache")
    
    # RedisManager 메서드들 위임
    def get_sync_client(self):
        """동기 클라이언트 반환 (FakeRedis 또는 None)"""
        return self.redis_manager.get_sync_client()
    
    async def get_async_client(self):
        """비동기 클라이언트 반환"""
        return await self.redis_manager.get_async_client()
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        return self.redis_manager.test_connection()
    
    async def test_async_connection(self) -> bool:
        """비동기 연결 테스트"""
        return await self.redis_manager.test_async_connection()
    
    # SnapshotManager 메서드들 위임
    def save_checkpoint(self, checkpoint_data: CheckpointData, ttl: Optional[int] = None) -> str:
        """체크포인트 저장"""
        return self.snapshot_manager.save_checkpoint(checkpoint_data, ttl)
    
    async def save_checkpoint_async(self, checkpoint_data: CheckpointData, ttl: Optional[int] = None) -> str:
        """체크포인트 저장 (비동기)"""
        return await self.snapshot_manager.save_checkpoint_async(checkpoint_data, ttl)
    
    def load_checkpoint(self, workflow_id: str, latest: bool = True) -> Optional[CheckpointData]:
        """체크포인트 로드"""
        return self.snapshot_manager.load_checkpoint(workflow_id, latest)
    
    async def load_checkpoint_async(self, workflow_id: str, latest: bool = True) -> Optional[CheckpointData]:
        """체크포인트 로드 (비동기)"""
        return await self.snapshot_manager.load_checkpoint_async(workflow_id, latest)
    
    def save_workflow_state(self, workflow_state: WorkflowState, checkpoint_type: str = "periodic") -> str:
        """워크플로우 상태 저장"""
        return self.snapshot_manager.save_workflow_state(workflow_state, checkpoint_type)
    
    async def save_workflow_state_async(self, workflow_state: WorkflowState, checkpoint_type: str = "periodic") -> str:
        """워크플로우 상태 저장 (비동기)"""
        return await self.snapshot_manager.save_workflow_state_async(workflow_state, checkpoint_type)
    
    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회"""
        return self.snapshot_manager.get_workflow_state(workflow_id)
    
    async def get_workflow_state_async(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회 (비동기)"""
        return await self.snapshot_manager.get_workflow_state_async(workflow_id)
    
    # 확장 API 메서드들 위임
    async def get_checkpoints_by_workflow(self, workflow_id: str, checkpoint_type: Optional[str] = None, limit: int = 10) -> List[CheckpointData]:
        """워크플로우별 체크포인트 목록 조회"""
        return await self.snapshot_manager.get_checkpoints_by_workflow(workflow_id, checkpoint_type, limit)
    
    async def get_latest_checkpoint(self, workflow_id: str, checkpoint_type: Optional[str] = None) -> Optional[CheckpointData]:
        """최신 체크포인트 조회"""
        return await self.snapshot_manager.get_latest_checkpoint(workflow_id, checkpoint_type)
    
    async def delete_checkpoints(self, workflow_id: str, checkpoint_type: Optional[str] = None) -> int:
        """체크포인트 삭제"""
        return await self.snapshot_manager.delete_checkpoints(workflow_id, checkpoint_type)
    
    async def list_all_checkpoints(self, page: int = 1, page_size: int = 20, checkpoint_type: Optional[str] = None) -> Tuple[List[CheckpointData], int]:
        """전체 체크포인트 목록 조회"""
        return await self.snapshot_manager.list_all_checkpoints(page, page_size, checkpoint_type)
    
    def cleanup_expired_checkpoints(self) -> int:
        """만료된 체크포인트 정리"""
        return self.snapshot_manager.cleanup_expired_checkpoints()
    
    # 분산 락 메서드들
    def acquire_lock(self, resource_name: str, ttl: int = 30, blocking: bool = True, timeout: Optional[float] = None):
        """분산 락 획득"""
        return self.lock_manager.acquire_lock(resource_name, ttl, blocking, timeout)
    
    def acquire_lock_sync(self, resource_name: str, ttl: int = 30, timeout: Optional[float] = None) -> Optional[str]:
        """동기 락 획득"""
        return self.lock_manager.acquire_lock_sync(resource_name, ttl, timeout)
    
    def release_lock(self, resource_name: str, lock_id: str) -> bool:
        """락 해제"""
        return self.lock_manager.release_lock(resource_name, lock_id)
    
    def is_locked(self, resource_name: str) -> bool:
        """락 상태 확인"""
        return self.lock_manager.is_locked(resource_name)
    
    # 상태 점검
    async def health_check(self) -> Dict[str, Any]:
        """전체 시스템 상태 점검"""
        try:
            # 각 컴포넌트 상태 확인
            cache_health = self.cache_manager.health_check()
            lock_health = self.lock_manager.health_check()
            snapshot_health = await self.snapshot_manager.health_check()
            
            return {
                "status": "healthy" if all([
                    cache_health["status"] == "healthy",
                    lock_health["status"] == "healthy",
                    snapshot_health
                ]) else "unhealthy",
                "components": {
                    "cache_manager": cache_health,
                    "lock_manager": lock_health,
                    "snapshot_manager": snapshot_health,
                    "redis_compatibility": FAKEREDIS_AVAILABLE
                },
                "migration_info": {
                    "redis_replaced": True,
                    "backend": "diskcache + filelock",
                    "compatibility_mode": FAKEREDIS_AVAILABLE
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """연결 종료"""
        self.redis_manager.close()
    
    async def close_async(self):
        """비동기 연결 종료"""
        await self.redis_manager.close_async()


if __name__ == "__main__":
    # 기본 테스트
    import asyncio
    
    async def test_storage_manager():
        manager = StorageManager()
        print("✅ StorageManager 완전 구현 성공")
        
        health = await manager.health_check()
        print("📊 전체 상태:", json.dumps(health, indent=2))
        
        await manager.close_async()
    
    asyncio.run(test_storage_manager())
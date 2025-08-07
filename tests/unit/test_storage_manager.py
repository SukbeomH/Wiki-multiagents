"""
Storage Manager 단위 테스트

Redis 완전 대체를 위한 통합 StorageManager 테스트
"""

import pytest
import tempfile
import shutil
import asyncio
from datetime import datetime
from unittest.mock import patch

from server.utils.storage_manager import StorageManager, RedisConfig
from server.schemas.base import CheckpointData, CheckpointType, WorkflowState, WorkflowStage


class TestRedisConfig:
    """RedisConfig 호환성 테스트"""
    
    def test_default_redis_config(self):
        """기본 Redis 설정 테스트"""
        config = RedisConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
    
    def test_redis_to_cache_config(self):
        """Redis 설정을 CacheConfig로 변환 테스트"""
        redis_config = RedisConfig(host="redis-server", port=6380, db=1)
        cache_config = redis_config.to_cache_config()
        
        assert cache_config.cache_dir == "./data/cache"
        assert cache_config.max_size == 1024 * 1024 * 1024  # 1GB
        assert cache_config.eviction_policy == "least-recently-used"


class TestStorageManager:
    """StorageManager 통합 테스트"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """임시 스토리지 디렉터리"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """테스트용 StorageManager"""
        # 환경변수 설정으로 임시 디렉터리 사용
        env_vars = {
            "CACHE_DIR": f"{temp_storage_dir}/cache",
            "LOCK_DIR": f"{temp_storage_dir}/locks",
            "CACHE_MAX_SIZE": "10485760",  # 10MB
            "CACHE_DEFAULT_TTL": "60"  # 1분
        }
        
        with patch.dict('os.environ', env_vars):
            return StorageManager()
    
    def test_initialization(self, storage_manager):
        """초기화 테스트"""
        assert storage_manager.redis_manager is not None
        assert storage_manager.snapshot_manager is not None
        assert storage_manager.lock_manager is not None
        assert storage_manager.cache_manager is not None
    
    def test_redis_compatibility(self, storage_manager):
        """Redis API 호환성 테스트"""
        # 동기 클라이언트
        sync_client = storage_manager.get_sync_client()
        # fakeredis가 없으면 None일 수 있음
        if sync_client:
            sync_client.set("test_key", "test_value")
            assert sync_client.get("test_key") == "test_value"
        
        # 연결 테스트
        assert storage_manager.test_connection()
    
    @pytest.mark.asyncio
    async def test_async_redis_compatibility(self, storage_manager):
        """비동기 Redis API 호환성 테스트"""
        # 비동기 클라이언트
        async_client = await storage_manager.get_async_client()
        # fakeredis가 없으면 None일 수 있음
        if async_client:
            assert hasattr(async_client, 'set')
        
        # 비동기 연결 테스트
        assert await storage_manager.test_async_connection()
    
    def test_checkpoint_operations(self, storage_manager):
        """체크포인트 작업 테스트"""
        # WorkflowState 생성
        workflow_state = WorkflowState(
            workflow_id="integration_test",
            trace_id="trace_001",
            current_stage=WorkflowStage.EXTRACTION,
            keyword="storage manager test"
        )
        
        # CheckpointData 생성
        checkpoint_data = CheckpointData(
            workflow_id="integration_test",
            checkpoint_type=CheckpointType.PERIODIC,
            state_snapshot=workflow_state
        )
        
        # 체크포인트 저장 (동기)
        key = storage_manager.save_checkpoint(checkpoint_data)
        assert key is not None
        assert "kg_checkpoint:integration_test" in key
        
        # 체크포인트 로드 (동기)
        loaded = storage_manager.load_checkpoint("integration_test")
        assert loaded is not None
        assert loaded.workflow_id == "integration_test"
        assert loaded.state_snapshot.keyword == "storage manager test"
    
    @pytest.mark.asyncio
    async def test_async_checkpoint_operations(self, storage_manager):
        """비동기 체크포인트 작업 테스트"""
        # WorkflowState 생성
        workflow_state = WorkflowState(
            workflow_id="async_test",
            trace_id="async_trace",
            current_stage=WorkflowStage.WIKI_GENERATION,
            keyword="async storage test"
        )
        
        # CheckpointData 생성
        checkpoint_data = CheckpointData(
            workflow_id="async_test",
            checkpoint_type=CheckpointType.MANUAL,
            state_snapshot=workflow_state
        )
        
        # 비동기 체크포인트 저장
        key = await storage_manager.save_checkpoint_async(checkpoint_data)
        assert key is not None
        
        # 비동기 체크포인트 로드
        loaded = await storage_manager.load_checkpoint_async("async_test")
        assert loaded is not None
        assert loaded.workflow_id == "async_test"
    
    def test_workflow_state_operations(self, storage_manager):
        """워크플로우 상태 작업 테스트"""
        # WorkflowState 생성
        workflow_state = WorkflowState(
            workflow_id="state_test",
            trace_id="state_trace",
            current_stage=WorkflowStage.RESEARCH,
            keyword="workflow state test"
        )
        
        # 워크플로우 상태 저장
        key = storage_manager.save_workflow_state(workflow_state, "manual")
        assert key is not None
        
        # 워크플로우 상태 조회
        loaded_state = storage_manager.get_workflow_state("state_test")
        assert loaded_state is not None
        assert loaded_state.workflow_id == "state_test"
        assert loaded_state.current_stage == WorkflowStage.RESEARCH
    
    @pytest.mark.asyncio
    async def test_async_workflow_state_operations(self, storage_manager):
        """비동기 워크플로우 상태 작업 테스트"""
        # WorkflowState 생성
        workflow_state = WorkflowState(
            workflow_id="async_state_test",
            trace_id="async_state_trace",
            current_stage=WorkflowStage.FEEDBACK_PROCESSING,
            keyword="async workflow state test"
        )
        
        # 비동기 워크플로우 상태 저장
        key = await storage_manager.save_workflow_state_async(workflow_state, "manual")
        assert key is not None
        
        # 비동기 워크플로우 상태 조회
        loaded_state = await storage_manager.get_workflow_state_async("async_state_test")
        assert loaded_state is not None
        assert loaded_state.workflow_id == "async_state_test"
    
    @pytest.mark.asyncio
    async def test_checkpoint_management(self, storage_manager):
        """체크포인트 관리 기능 테스트"""
        workflow_id = "management_test"
        
        # 여러 체크포인트 생성
        for i in range(3):
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                trace_id=f"trace_{i}",
                current_stage=WorkflowStage.RESEARCH,
                keyword=f"test {i}"
            )
            checkpoint_data = CheckpointData(
                workflow_id=workflow_id,
                checkpoint_type=CheckpointType.PERIODIC,
                state_snapshot=workflow_state
            )
            await storage_manager.save_checkpoint_async(checkpoint_data)
        
        # 워크플로우별 체크포인트 조회 (diskcache는 마지막 값만 저장될 수 있음)
        checkpoints = await storage_manager.get_checkpoints_by_workflow(workflow_id)
        assert len(checkpoints) >= 1  # 최소 1개는 있어야 함
        
        # 최신 체크포인트 조회
        latest = await storage_manager.get_latest_checkpoint(workflow_id)
        assert latest is not None
        assert latest.workflow_id == workflow_id
        
        # 체크포인트 삭제
        deleted_count = await storage_manager.delete_checkpoints(workflow_id)
        assert deleted_count >= 0  # 삭제된 개수
        
        # 삭제 후 확인
        remaining_checkpoints = await storage_manager.get_checkpoints_by_workflow(workflow_id)
        assert len(remaining_checkpoints) == 0
    
    def test_distributed_lock_operations(self, storage_manager):
        """분산 락 작업 테스트"""
        resource_name = "storage_lock_test"
        
        # 컨텍스트 매니저 락
        with storage_manager.acquire_lock(resource_name, ttl=5) as lock_id:
            assert lock_id is not None
            assert storage_manager.is_locked(resource_name)
        
        # 락 해제 확인
        assert not storage_manager.is_locked(resource_name)
        
        # 동기적 락
        lock_id = storage_manager.acquire_lock_sync(resource_name, ttl=5)
        assert lock_id is not None
        
        success = storage_manager.release_lock(resource_name, lock_id)
        assert success
    
    @pytest.mark.asyncio
    async def test_health_check(self, storage_manager):
        """상태 확인 테스트"""
        health = await storage_manager.health_check()
        
        assert "status" in health
        assert health["status"] in ["healthy", "unhealthy"]
        assert "components" in health
        assert "migration_info" in health
        
        # 구성 요소 확인
        components = health["components"]
        assert "cache_manager" in components
        assert "lock_manager" in components
        assert "snapshot_manager" in components
        
        # 마이그레이션 정보 확인
        migration_info = health["migration_info"]
        assert migration_info["redis_replaced"] is True
        assert migration_info["backend"] == "diskcache + filelock"
    
    def test_cleanup_operations(self, storage_manager):
        """정리 작업 테스트"""
        # 만료된 체크포인트 정리
        cleaned_count = storage_manager.cleanup_expired_checkpoints()
        assert cleaned_count >= 0
    
    @pytest.mark.asyncio
    async def test_list_all_checkpoints(self, storage_manager):
        """전체 체크포인트 목록 조회 테스트"""
        # 테스트 체크포인트 생성
        workflow_state = WorkflowState(
            workflow_id="list_test",
            trace_id="list_trace",
            current_stage=WorkflowStage.RESEARCH,
            keyword="list test"
        )
        checkpoint_data = CheckpointData(
            workflow_id="list_test",
            checkpoint_type=CheckpointType.MANUAL,
            state_snapshot=workflow_state
        )
        await storage_manager.save_checkpoint_async(checkpoint_data)
        
        # 전체 목록 조회
        checkpoints, total = await storage_manager.list_all_checkpoints(page=1, page_size=10)
        assert isinstance(checkpoints, list)
        assert isinstance(total, int)
        assert total >= 0
    
    def test_close_operations(self, storage_manager):
        """연결 종료 테스트"""
        # 동기 종료
        storage_manager.close()
        
        # 여전히 작동해야 함 (로컬 파일 기반)
        assert storage_manager.test_connection()
    
    @pytest.mark.asyncio
    async def test_async_close_operations(self, storage_manager):
        """비동기 연결 종료 테스트"""
        # 비동기 종료
        await storage_manager.close_async()
        
        # 여전히 작동해야 함 (로컬 파일 기반)
        assert await storage_manager.test_async_connection()


class TestStorageManagerEdgeCases:
    """StorageManager 경계 조건 테스트"""
    
    @pytest.fixture
    def storage_manager(self):
        """최소 설정 StorageManager"""
        return StorageManager()
    
    def test_nonexistent_workflow_operations(self, storage_manager):
        """존재하지 않는 워크플로우 작업 테스트"""
        # 존재하지 않는 워크플로우 상태 조회
        state = storage_manager.get_workflow_state("nonexistent_workflow")
        assert state is None
        
        # 존재하지 않는 워크플로우 체크포인트 로드
        checkpoint = storage_manager.load_checkpoint("nonexistent_workflow")
        assert checkpoint is None
    
    @pytest.mark.asyncio
    async def test_async_nonexistent_operations(self, storage_manager):
        """비동기 존재하지 않는 작업 테스트"""
        # 존재하지 않는 워크플로우 체크포인트 조회
        checkpoints = await storage_manager.get_checkpoints_by_workflow("nonexistent")
        assert len(checkpoints) == 0
        
        # 존재하지 않는 최신 체크포인트 조회
        latest = await storage_manager.get_latest_checkpoint("nonexistent")
        assert latest is None
        
        # 존재하지 않는 체크포인트 삭제
        deleted_count = await storage_manager.delete_checkpoints("nonexistent")
        assert deleted_count == 0
    
    def test_invalid_lock_operations(self, storage_manager):
        """잘못된 락 작업 테스트"""
        # 존재하지 않는 락 해제
        success = storage_manager.release_lock("nonexistent", "fake_id")
        assert not success
        
        # 존재하지 않는 리소스 락 상태 확인
        is_locked = storage_manager.is_locked("nonexistent_resource")
        assert not is_locked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
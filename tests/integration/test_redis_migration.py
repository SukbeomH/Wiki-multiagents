"""
Redis 마이그레이션 통합 테스트

전체 시스템의 Redis → diskcache 마이그레이션 검증
"""

import pytest
import tempfile
import shutil
import asyncio
import time
import threading
from datetime import datetime
from unittest.mock import patch

from server.utils.storage_manager import StorageManager
from server.utils.cache_manager import CacheManager, CacheConfig  
from server.utils.lock_manager import DistributedLockManager
from server.schemas.base import CheckpointData, CheckpointType, WorkflowState, WorkflowStage


class TestRedisMigrationIntegration:
    """Redis 마이그레이션 통합 테스트"""
    
    @pytest.fixture
    def temp_integration_dir(self):
        """통합 테스트용 임시 디렉터리"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def integrated_storage(self, temp_integration_dir):
        """통합 테스트용 스토리지 시스템"""
        env_vars = {
            "CACHE_DIR": f"{temp_integration_dir}/cache",
            "LOCK_DIR": f"{temp_integration_dir}/locks",
            "CACHE_MAX_SIZE": "52428800",  # 50MB
            "CACHE_DEFAULT_TTL": "300",  # 5분
            "CACHE_CHECKPOINT_TTL": "3600"  # 1시간
        }
        
        with patch.dict('os.environ', env_vars):
            return StorageManager()
    
    def test_full_workflow_simulation(self, integrated_storage):
        """전체 워크플로우 시뮬레이션 테스트"""
        workflow_id = "integration_workflow_001"
        
        # 1. 분산 락으로 워크플로우 시작 보호
        with integrated_storage.acquire_lock(f"workflow:{workflow_id}", ttl=30) as lock_id:
            assert lock_id is not None
            
            # 2. 초기 워크플로우 상태 저장
            initial_state = WorkflowState(
                workflow_id=workflow_id,
                trace_id="trace_001",
                current_stage=WorkflowStage.RESEARCH,
                keyword="integration test workflow"
            )
            
            checkpoint_key = integrated_storage.save_workflow_state(initial_state, "manual")
            assert checkpoint_key is not None
            
            # 3. 워크플로우 진행 시뮬레이션
            stages = [
                WorkflowStage.EXTRACTION,
                WorkflowStage.RETRIEVAL,
                WorkflowStage.WIKI_GENERATION,
                WorkflowStage.FEEDBACK
            ]
            
            for stage in stages:
                # 단계별 상태 업데이트
                current_state = WorkflowState(
                    workflow_id=workflow_id,
                    trace_id="trace_001",
                    current_stage=stage,
                    keyword="integration test workflow"
                )
                
                # 체크포인트 저장
                checkpoint_data = CheckpointData(
                    workflow_id=workflow_id,
                    checkpoint_type=CheckpointType.PERIODIC,
                    state_snapshot=current_state
                )
                
                checkpoint_key = integrated_storage.save_checkpoint(checkpoint_data)
                assert checkpoint_key is not None
                
                # 중간 데이터 캐싱 시뮬레이션
                cache_key = f"stage_data:{workflow_id}:{stage.value}"
                stage_data = {
                    "stage": stage.value,
                    "timestamp": datetime.now().isoformat(),
                    "data": f"processed data for {stage.value}"
                }
                
                # JSON 캐싱
                integrated_storage.cache_manager.json_set(cache_key, "$", stage_data)
                cached_data = integrated_storage.cache_manager.json_get(cache_key, "$")
                assert cached_data == stage_data
        
        # 4. 락 해제 후 최종 상태 확인
        assert not integrated_storage.is_locked(f"workflow:{workflow_id}")
        
        # 5. 저장된 체크포인트 검증
        checkpoints = asyncio.run(
            integrated_storage.get_checkpoints_by_workflow(workflow_id)
        )
        assert len(checkpoints) >= len(stages)  # 최소 각 단계별 체크포인트
        
        # 6. 최신 상태 확인
        final_state = integrated_storage.get_workflow_state(workflow_id)
        assert final_state is not None
        assert final_state.current_stage == WorkflowStage.FEEDBACK
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_management(self, integrated_storage):
        """동시 워크플로우 관리 테스트"""
        workflows = ["concurrent_wf_001", "concurrent_wf_002", "concurrent_wf_003"]
        results = []
        
        async def process_workflow(workflow_id, delay=0):
            """개별 워크플로우 처리"""
            try:
                if delay:
                    await asyncio.sleep(delay)
                
                # 워크플로우별 락 획득
                with integrated_storage.acquire_lock(f"wf:{workflow_id}", ttl=10) as lock_id:
                    if lock_id is None:
                        results.append((workflow_id, False, "Lock failed"))
                        return
                    
                    # 워크플로우 상태 생성 및 저장
                    workflow_state = WorkflowState(
                        workflow_id=workflow_id,
                        trace_id=f"trace_{workflow_id}",
                        current_stage=WorkflowStage.RESEARCH,
                        keyword=f"concurrent test {workflow_id}"
                    )
                    
                    # 비동기 저장
                    checkpoint_key = await integrated_storage.save_workflow_state_async(
                        workflow_state, "concurrent_test"
                    )
                    
                    # 저장 검증
                    loaded_state = await integrated_storage.get_workflow_state_async(workflow_id)
                    
                    success = (
                        checkpoint_key is not None and
                        loaded_state is not None and
                        loaded_state.workflow_id == workflow_id
                    )
                    
                    results.append((workflow_id, success, "Completed"))
                    
            except Exception as e:
                results.append((workflow_id, False, str(e)))
        
        # 동시 워크플로우 실행
        tasks = [
            process_workflow(wf_id, delay=i*0.1)
            for i, wf_id in enumerate(workflows)
        ]
        
        await asyncio.gather(*tasks)
        
        # 결과 검증
        assert len(results) == len(workflows)
        successful_workflows = sum(1 for _, success, _ in results if success)
        assert successful_workflows == len(workflows)
        
        # 각 워크플로우 상태 확인
        for workflow_id in workflows:
            state = await integrated_storage.get_workflow_state_async(workflow_id)
            assert state is not None
            assert state.workflow_id == workflow_id
    
    def test_performance_comparison_simulation(self, integrated_storage):
        """성능 비교 시뮬레이션 테스트"""
        operations = []
        
        # 1. 대량 캐시 작업 성능 테스트
        start_time = time.time()
        
        for i in range(100):
            key = f"perf_test:{i}"
            data = {"id": i, "data": f"performance test data {i}" * 10}
            
            # JSON 저장
            integrated_storage.cache_manager.json_set(key, "$", data)
            
            # JSON 조회
            retrieved = integrated_storage.cache_manager.json_get(key, "$")
            assert retrieved == data
            
            operations.append(("cache", time.time() - start_time))
        
        cache_time = time.time() - start_time
        
        # 2. 대량 락 작업 성능 테스트
        start_time = time.time()
        
        for i in range(50):
            resource = f"perf_lock_{i}"
            
            lock_id = integrated_storage.acquire_lock_sync(resource, ttl=1)
            assert lock_id is not None
            
            success = integrated_storage.release_lock(resource, lock_id)
            assert success
            
            operations.append(("lock", time.time() - start_time))
        
        lock_time = time.time() - start_time
        
        # 3. 체크포인트 저장/조회 성능 테스트
        start_time = time.time()
        
        for i in range(20):
            workflow_state = WorkflowState(
                workflow_id=f"perf_wf_{i}",
                trace_id=f"perf_trace_{i}",
                current_stage=WorkflowStage.RESEARCH,
                keyword=f"performance test {i}"
            )
            
            checkpoint_data = CheckpointData(
                workflow_id=f"perf_wf_{i}",
                checkpoint_type=CheckpointType.PERIODIC,
                state_snapshot=workflow_state
            )
            
            # 체크포인트 저장
            key = integrated_storage.save_checkpoint(checkpoint_data)
            assert key is not None
            
            # 체크포인트 조회
            loaded = integrated_storage.load_checkpoint(f"perf_wf_{i}")
            assert loaded is not None
            
            operations.append(("checkpoint", time.time() - start_time))
        
        checkpoint_time = time.time() - start_time
        
        # 성능 결과 출력 (테스트 로그)
        print(f"\n=== 성능 테스트 결과 ===")
        print(f"캐시 작업 (100회): {cache_time:.4f}초")
        print(f"락 작업 (50회): {lock_time:.4f}초")
        print(f"체크포인트 작업 (20회): {checkpoint_time:.4f}초")
        
        # 성능 기준 검증 (합리적인 시간 내 완료)
        assert cache_time < 10.0  # 10초 내
        assert lock_time < 5.0   # 5초 내
        assert checkpoint_time < 5.0  # 5초 내
    
    def test_data_consistency_validation(self, integrated_storage):
        """데이터 일관성 검증 테스트"""
        workflow_id = "consistency_test"
        
        # 1. 복잡한 JSON 데이터 일관성 테스트
        complex_data = {
            "workflow": {
                "id": workflow_id,
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "stages": ["research", "extraction", "retrieval"],
                    "config": {
                        "max_retries": 3,
                        "timeout": 30,
                        "enable_cache": True
                    }
                },
                "results": [
                    {"stage": "research", "status": "completed", "data": ["item1", "item2"]},
                    {"stage": "extraction", "status": "in_progress", "data": None}
                ]
            }
        }
        
        # JSON 저장 및 검증
        integrated_storage.cache_manager.json_set("complex_data", "$", complex_data)
        retrieved_data = integrated_storage.cache_manager.json_get("complex_data", "$")
        assert retrieved_data == complex_data
        
        # 부분 업데이트 및 검증
        integrated_storage.cache_manager.json_set(
            "complex_data", "$.workflow.results[1].status", "completed"
        )
        updated_status = integrated_storage.cache_manager.json_get(
            "complex_data", "$.workflow.results[1].status"
        )
        assert updated_status == "completed"
        
        # 2. 체크포인트 데이터 일관성 테스트
        workflow_state = WorkflowState(
            workflow_id=workflow_id,
            trace_id="consistency_trace",
            current_stage=WorkflowStage.EXTRACTION,
            keyword="consistency validation test"
        )
        
        checkpoint_data = CheckpointData(
            workflow_id=workflow_id,
            checkpoint_type=CheckpointType.MANUAL,
            state_snapshot=workflow_state
        )
        
        # 여러 번 저장하여 일관성 확인
        keys = []
        for i in range(5):
            key = integrated_storage.save_checkpoint(checkpoint_data)
            keys.append(key)
            assert key is not None
        
        # 모든 체크포인트 검증
        for key in keys:
            loaded = integrated_storage.get_checkpoint(key)
            assert loaded is not None
            assert loaded.workflow_id == workflow_id
            assert loaded.state_snapshot.keyword == "consistency validation test"
    
    def test_error_recovery_and_resilience(self, integrated_storage):
        """오류 복구 및 복원력 테스트"""
        
        # 1. 잘못된 데이터 처리 테스트
        with pytest.raises(Exception):
            # 잘못된 JSON 경로
            integrated_storage.cache_manager.json_set("test", "invalid_path", "data")
        
        # 2. 락 타임아웃 및 복구 테스트
        resource = "recovery_test_resource"
        
        # 첫 번째 락 획득
        lock_id1 = integrated_storage.acquire_lock_sync(resource, ttl=1, timeout=0.1)
        assert lock_id1 is not None
        
        # 두 번째 락 시도 (실패해야 함)
        lock_id2 = integrated_storage.acquire_lock_sync(resource, ttl=1, timeout=0.1)
        assert lock_id2 is None
        
        # 첫 번째 락 해제 후 재시도 (성공해야 함)
        integrated_storage.release_lock(resource, lock_id1)
        lock_id3 = integrated_storage.acquire_lock_sync(resource, ttl=1, timeout=0.1)
        assert lock_id3 is not None
        integrated_storage.release_lock(resource, lock_id3)
        
        # 3. 체크포인트 데이터 손상 시뮬레이션
        # 잘못된 워크플로우 ID로 조회 (오류 없이 None 반환)
        invalid_checkpoint = integrated_storage.load_checkpoint("invalid_workflow_id")
        assert invalid_checkpoint is None
        
        # 존재하지 않는 체크포인트 키로 조회
        invalid_direct = integrated_storage.get_checkpoint("invalid_checkpoint_key")
        assert invalid_direct is None
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, integrated_storage):
        """시스템 상태 모니터링 테스트"""
        
        # 1. 전체 시스템 상태 확인
        health = await integrated_storage.health_check()
        
        assert health["status"] in ["healthy", "unhealthy"]
        assert "components" in health
        assert "migration_info" in health
        
        # 2. 구성 요소별 상태 확인
        components = health["components"]
        required_components = ["cache_manager", "lock_manager", "snapshot_manager"]
        
        for component in required_components:
            assert component in components
            # 각 구성 요소가 상태 정보를 제공해야 함
            assert isinstance(components[component], (dict, bool))
        
        # 3. 마이그레이션 정보 확인
        migration_info = health["migration_info"]
        assert migration_info["redis_replaced"] is True
        assert "backend" in migration_info
        assert "diskcache" in migration_info["backend"]
        
        # 4. 개별 구성 요소 상태 확인
        cache_health = integrated_storage.cache_manager.health_check()
        assert cache_health["status"] == "healthy"
        
        lock_health = integrated_storage.lock_manager.health_check()
        assert lock_health["status"] in ["healthy", "error"]
        
        snapshot_health = await integrated_storage.snapshot_manager.health_check()
        assert isinstance(snapshot_health, bool)
    
    def test_cleanup_and_maintenance(self, integrated_storage):
        """정리 및 유지보수 기능 테스트"""
        
        # 1. 만료된 체크포인트 정리
        initial_cleanup = integrated_storage.cleanup_expired_checkpoints()
        assert initial_cleanup >= 0
        
        # 2. 테스트 데이터 생성 후 정리
        test_workflows = []
        for i in range(5):
            workflow_id = f"cleanup_test_{i}"
            test_workflows.append(workflow_id)
            
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                trace_id=f"cleanup_trace_{i}",
                current_stage=WorkflowStage.RESEARCH,
                keyword=f"cleanup test {i}"
            )
            
            integrated_storage.save_workflow_state(workflow_state, "cleanup_test")
        
        # 3. 생성된 데이터 확인
        for workflow_id in test_workflows:
            state = integrated_storage.get_workflow_state(workflow_id)
            assert state is not None
        
        # 4. 개별 워크플로우 정리
        for workflow_id in test_workflows:
            deleted = asyncio.run(
                integrated_storage.delete_checkpoints(workflow_id)
            )
            assert deleted >= 0
            
            # 정리 후 확인
            remaining_state = integrated_storage.get_workflow_state(workflow_id)
            # 정리 후에는 해당 워크플로우의 최신 상태가 없어야 함
            assert remaining_state is None
        
        # 5. 캐시 정리
        integrated_storage.cache_manager.clear()
        
        # 6. 만료된 락 정리
        cleaned_locks = integrated_storage.lock_manager.cleanup_expired_locks()
        assert cleaned_locks >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
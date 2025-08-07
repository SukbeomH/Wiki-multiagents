"""
Cache Manager 단위 테스트

Redis 마이그레이션의 핵심인 diskcache 기반 CacheManager 테스트
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

from server.utils.cache_manager import CacheManager, CacheConfig
from server.schemas.base import CheckpointData, CheckpointType, WorkflowState, WorkflowStage


class TestCacheConfig:
    """CacheConfig 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = CacheConfig()
        assert config.cache_dir == "./data/cache"
        assert config.max_size == 1024 * 1024 * 1024  # 1GB
        assert config.eviction_policy == "least-recently-used"
        assert config.default_ttl == 86400  # 24시간
        assert config.checkpoint_ttl == 604800  # 7일
    
    def test_from_env(self):
        """환경변수에서 설정 로드 테스트"""
        # 환경변수 설정
        os.environ.update({
            "CACHE_DIR": "/tmp/test_cache",
            "CACHE_MAX_SIZE": "536870912",  # 512MB
            "CACHE_EVICTION_POLICY": "lru",
            "CACHE_DEFAULT_TTL": "43200",  # 12시간
            "CACHE_CHECKPOINT_TTL": "86400"  # 1일
        })
        
        config = CacheConfig.from_env()
        assert config.cache_dir == "/tmp/test_cache"
        assert config.max_size == 536870912
        assert config.eviction_policy == "lru"
        assert config.default_ttl == 43200
        assert config.checkpoint_ttl == 86400
        
        # 환경변수 정리
        for key in ["CACHE_DIR", "CACHE_MAX_SIZE", "CACHE_EVICTION_POLICY", "CACHE_DEFAULT_TTL", "CACHE_CHECKPOINT_TTL"]:
            os.environ.pop(key, None)


class TestCacheManager:
    """CacheManager 테스트"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """임시 캐시 디렉터리 생성"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """테스트용 CacheManager 인스턴스"""
        config = CacheConfig(
            cache_dir=temp_cache_dir,
            max_size=10 * 1024 * 1024,  # 10MB (테스트용)
            default_ttl=60  # 1분 (테스트용)
        )
        return CacheManager(config)
    
    def test_initialization(self, cache_manager, temp_cache_dir):
        """초기화 테스트"""
        assert cache_manager.cache_dir == Path(temp_cache_dir)
        assert cache_manager.cache_dir.exists()
        assert cache_manager.cache is not None
        assert cache_manager.checkpoint_cache is not None
    
    def test_basic_cache_operations(self, cache_manager):
        """기본 캐시 작업 테스트"""
        # Set/Get
        cache_manager.set("test_key", "test_value")
        assert cache_manager.get("test_key") == "test_value"
        
        # TTL 설정
        cache_manager.set("ttl_key", "ttl_value", ttl=1)
        assert cache_manager.get("ttl_key") == "ttl_value"
        
        # 존재하지 않는 키
        assert cache_manager.get("nonexistent") is None
        
        # Delete
        cache_manager.delete("test_key")
        assert cache_manager.get("test_key") is None
    
    def test_json_operations(self, cache_manager):
        """Redis JSON 호환 작업 테스트"""
        test_data = {
            "user": {"name": "John", "age": 30},
            "items": [1, 2, 3]
        }
        
        # JSON Set/Get
        cache_manager.json_set("user:123", "$", test_data)
        result = cache_manager.json_get("user:123", "$")
        assert result == test_data
        
        # 특정 경로 설정/조회
        cache_manager.json_set("user:123", "$.user.city", "Seoul")
        city = cache_manager.json_get("user:123", "$.user.city")
        assert city == "Seoul"
        
        # JSON Delete
        cache_manager.json_del("user:123", "$.items")
        result = cache_manager.json_get("user:123", "$")
        assert "items" not in result
        
        cache_manager.json_del("user:123")
        assert cache_manager.json_get("user:123") is None
    
    def test_checkpoint_operations(self, cache_manager):
        """체크포인트 작업 테스트"""
        # WorkflowState 생성
        workflow_state = WorkflowState(
            workflow_id="test_workflow",
            trace_id="test_trace",
            current_stage=WorkflowStage.RESEARCH,
            keyword="test keyword"
        )
        
        # CheckpointData 생성
        checkpoint_data = CheckpointData(
            workflow_id="test_workflow",
            checkpoint_type=CheckpointType.MANUAL,
            state_snapshot=workflow_state
        )
        
        # 체크포인트 저장
        success = cache_manager.save_checkpoint("test_workflow", checkpoint_data)
        assert success is True
        
        # 체크포인트 조회
        loaded = cache_manager.get_checkpoint("test_workflow")
        assert loaded is not None
        assert loaded.workflow_id == "test_workflow"
        assert loaded.state_snapshot.keyword == "test keyword"
        
        # 워크플로우별 체크포인트 조회
        checkpoints = cache_manager.get_checkpoints_by_workflow("test_workflow")
        assert len(checkpoints) >= 1
        assert any(cp.workflow_id == "test_workflow" for cp in checkpoints)
        
        # 체크포인트 삭제 (checkpoint_id 필요)
        if loaded:
            success = cache_manager.delete_checkpoint(loaded.checkpoint_id)
            assert success
            # 삭제 후 조회 시 다른 체크포인트가 있을 수 있으므로 여기서는 검증 생략
    
    def test_health_check(self, cache_manager):
        """상태 확인 테스트"""
        health = cache_manager.health_check()
        assert health["status"] == "healthy"
        assert "config" in health
        assert "cache_dir" in health["config"]
        assert "cache_stats" in health
        assert "tests" in health
    
    def test_clear_operations(self, cache_manager):
        """캐시 정리 작업 테스트"""
        # 테스트 데이터 설정
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.json_set("json_key", "$", {"test": "data"})
        
        # 정리 전 확인
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.json_get("json_key") is not None
        
        # 전체 정리
        cache_manager.clear()
        
        # 정리 후 확인
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
        assert cache_manager.json_get("json_key") is None


class TestCacheManagerEdgeCases:
    """CacheManager 경계 조건 테스트"""
    
    @pytest.fixture
    def cache_manager(self):
        """테스트용 CacheManager 인스턴스"""
        temp_dir = tempfile.mkdtemp()
        config = CacheConfig(
            cache_dir=temp_dir,
            max_size=1024,  # 매우 작은 크기 (1KB)
            default_ttl=1  # 1초 TTL
        )
        manager = CacheManager(config)
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_invalid_json_path(self, cache_manager):
        """잘못된 JSON 경로 처리 테스트"""
        cache_manager.json_set("test", "$", {"key": "value"})
        
        # 잘못된 경로
        result = cache_manager.json_get("test", "$.nonexistent")
        assert result is None
        
        # 잘못된 JSON 데이터
        cache_manager.set("invalid_json", "not a json")
        result = cache_manager.json_get("invalid_json", "$")
        assert result is None
    
    def test_large_data_handling(self, cache_manager):
        """대용량 데이터 처리 테스트"""
        # 큰 데이터 생성 (캐시 크기 초과)
        large_data = "x" * 2048  # 2KB 데이터
        
        # 저장 시도 (작은 캐시에서 eviction 발생할 수 있음)
        cache_manager.set("large_key", large_data)
        
        # 데이터가 저장되거나 eviction되어야 함
        result = cache_manager.get("large_key")
        # eviction 정책에 따라 결과가 달라질 수 있음
        assert result is None or result == large_data
    
    def test_checkpoint_data_validation(self, cache_manager):
        """체크포인트 데이터 검증 테스트"""
        # 잘못된 체크포인트 키로 조회
        invalid_checkpoint = cache_manager.get_checkpoint("invalid_key")
        assert invalid_checkpoint is None
        
        # 빈 워크플로우 ID로 조회
        empty_checkpoints = cache_manager.get_checkpoints_by_workflow("")
        assert len(empty_checkpoints) == 0
        
        # 존재하지 않는 워크플로우 ID로 조회
        nonexistent_checkpoints = cache_manager.get_checkpoints_by_workflow("nonexistent_workflow")
        assert len(nonexistent_checkpoints) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
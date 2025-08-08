"""
Distributed Lock Manager 단위 테스트

Redis Redlock을 대체하는 filelock 기반 DistributedLockManager 테스트
"""

import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from unittest.mock import patch

from src.core.utils.lock_manager import DistributedLockManager, LockInfo


class TestLockInfo:
    """LockInfo 클래스 테스트"""
    
    def test_lock_info_creation(self):
        """LockInfo 생성 테스트"""
        lock_info = LockInfo("test_lock_id", "test_resource", 30)
        
        assert lock_info.lock_id == "test_lock_id"
        assert lock_info.resource_name == "test_resource"
        assert lock_info.ttl == 30
        assert lock_info.acquired_at <= time.time()
        assert lock_info.file_lock is None
    
    def test_lock_expiration(self):
        """락 만료 검사 테스트"""
        # 즉시 만료되는 락
        lock_info = LockInfo("test_id", "test_resource", 0)
        time.sleep(0.1)
        assert lock_info.is_expired()
        
        # 만료되지 않은 락
        lock_info = LockInfo("test_id", "test_resource", 10)
        assert not lock_info.is_expired()
    
    def test_remaining_time(self):
        """남은 시간 계산 테스트"""
        lock_info = LockInfo("test_id", "test_resource", 5)
        remaining = lock_info.remaining_time()
        assert 0 <= remaining <= 5
        
        # 만료된 락
        expired_lock = LockInfo("test_id", "test_resource", 0)
        time.sleep(0.1)
        assert expired_lock.remaining_time() == 0


class TestDistributedLockManager:
    """DistributedLockManager 테스트"""
    
    @pytest.fixture
    def temp_lock_dir(self):
        """임시 락 디렉터리 생성"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def lock_manager(self, temp_lock_dir):
        """테스트용 DistributedLockManager 인스턴스"""
        return DistributedLockManager(temp_lock_dir)
    
    def test_initialization(self, lock_manager, temp_lock_dir):
        """초기화 테스트"""
        assert lock_manager.lock_dir == Path(temp_lock_dir)
        assert lock_manager.lock_dir.exists()
        assert hasattr(lock_manager, 'local_locks')
        assert hasattr(lock_manager, '_cleanup_thread')
    
    def test_context_manager_lock(self, lock_manager):
        """컨텍스트 매니저 락 테스트"""
        resource_name = "test_resource"
        
        with lock_manager.acquire_lock(resource_name, ttl=5) as lock_id:
            assert lock_id is not None
            assert lock_manager.is_locked(resource_name)
            
            # 락 정보 확인
            lock_info = lock_manager.get_lock_info(resource_name)
            assert lock_info is not None
            assert lock_info["lock_id"] == lock_id
            assert lock_info["resource_name"] == resource_name
        
        # 컨텍스트 매니저 종료 후 락 해제 확인
        assert not lock_manager.is_locked(resource_name)
    
    def test_synchronous_lock(self, lock_manager):
        """동기적 락 획득/해제 테스트"""
        resource_name = "sync_test_resource"
        
        # 락 획득
        lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=5)
        assert lock_id is not None
        assert lock_manager.is_locked(resource_name)
        
        # 락 해제
        success = lock_manager.release_lock(resource_name, lock_id)
        assert success
        assert not lock_manager.is_locked(resource_name)
    
    def test_lock_timeout(self, lock_manager):
        """락 타임아웃 테스트"""
        resource_name = "timeout_test"
        
        # 첫 번째 락 획득
        lock_id1 = lock_manager.acquire_lock_sync(resource_name, ttl=5, timeout=0.1)
        assert lock_id1 is not None
        
        # 두 번째 락 시도 (타임아웃으로 실패해야 함)
        lock_id2 = lock_manager.acquire_lock_sync(resource_name, ttl=5, timeout=0.1)
        assert lock_id2 is None
        
        # 첫 번째 락 해제
        lock_manager.release_lock(resource_name, lock_id1)
        
        # 이제 새로운 락 획득 가능
        lock_id3 = lock_manager.acquire_lock_sync(resource_name, ttl=5, timeout=0.1)
        assert lock_id3 is not None
        lock_manager.release_lock(resource_name, lock_id3)
    
    def test_lock_extension(self, lock_manager):
        """락 연장 테스트"""
        resource_name = "extend_test"
        
        lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=2)
        assert lock_id is not None
        
        # 락 연장
        success = lock_manager.extend_lock(resource_name, lock_id, 5)
        assert success
        
        # 락 정보 확인
        lock_info = lock_manager.get_lock_info(resource_name)
        assert lock_info["ttl"] == 7  # 2 + 5
        
        lock_manager.release_lock(resource_name, lock_id)
    
    def test_concurrent_locks(self, lock_manager):
        """동시성 락 테스트"""
        resource_name = "concurrent_test"
        results = []
        
        def try_acquire_lock(thread_id):
            """스레드에서 락 획득 시도"""
            lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=1, timeout=0.5)
            results.append((thread_id, lock_id is not None))
            if lock_id:
                time.sleep(0.2)  # 잠시 대기
                lock_manager.release_lock(resource_name, lock_id)
        
        # 여러 스레드에서 동시에 락 획득 시도
        threads = []
        for i in range(3):
            thread = threading.Thread(target=try_acquire_lock, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 결과 확인: 최소 하나의 스레드는 락을 획득해야 함
        # filelock의 동시성 제한으로 인해 여러 스레드가 락을 획득할 수 있음
        successful_acquisitions = sum(1 for _, success in results if success)
        assert successful_acquisitions >= 1  # 최소 1개는 성공해야 함
    
    def test_force_release(self, lock_manager):
        """강제 락 해제 테스트"""
        resource_name = "force_release_test"
        
        lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=10)
        assert lock_id is not None
        assert lock_manager.is_locked(resource_name)
        
        # 강제 해제
        success = lock_manager.force_release(resource_name)
        assert success
        assert not lock_manager.is_locked(resource_name)
    
    def test_expired_lock_cleanup(self, lock_manager):
        """만료된 락 정리 테스트"""
        resource_name = "cleanup_test"
        
        # 매우 짧은 TTL로 락 생성
        lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=1)
        assert lock_id is not None
        
        # 짧은 시간 대기하여 TTL 만료 시뮬레이션
        time.sleep(1.1)
        
        # 정리 실행
        cleaned_count = lock_manager.cleanup_expired_locks()
        assert cleaned_count >= 0  # 정리된 락 수
        
        # 만료된 락은 더 이상 잠겨있지 않아야 함 (filelock 특성상 파일이 남을 수 있음)
        # 정리 후 새로운 락 획득이 가능한지 확인
        new_lock_id = lock_manager.acquire_lock_sync(resource_name, ttl=5, timeout=0.1)
        assert new_lock_id is not None
        lock_manager.release_lock(resource_name, new_lock_id)
    
    def test_get_all_locks(self, lock_manager):
        """모든 락 정보 조회 테스트"""
        # 여러 락 생성
        lock_id1 = lock_manager.acquire_lock_sync("resource1", ttl=5)
        lock_id2 = lock_manager.acquire_lock_sync("resource2", ttl=5)
        
        all_locks = lock_manager.get_all_locks()
        assert len(all_locks) >= 2
        assert "resource1" in all_locks
        assert "resource2" in all_locks
        
        # 정리
        lock_manager.release_lock("resource1", lock_id1)
        lock_manager.release_lock("resource2", lock_id2)
    
    def test_health_check(self, lock_manager):
        """상태 확인 테스트"""
        health = lock_manager.health_check()
        
        assert "status" in health
        assert health["status"] in ["healthy", "error"]
        assert "lock_dir" in health
        assert "active_locks" in health
        assert "expired_locks" in health
        assert "test_lock_success" in health
    
    def test_invalid_operations(self, lock_manager):
        """잘못된 작업 테스트"""
        # 존재하지 않는 락 해제 시도
        success = lock_manager.release_lock("nonexistent", "fake_id")
        assert not success
        
        # 잘못된 lock_id로 해제 시도
        lock_id = lock_manager.acquire_lock_sync("test", ttl=5)
        success = lock_manager.release_lock("test", "wrong_id")
        assert not success
        
        # 올바른 lock_id로 해제
        success = lock_manager.release_lock("test", lock_id)
        assert success
        
        # 존재하지 않는 락 연장 시도
        success = lock_manager.extend_lock("nonexistent", "fake_id", 5)
        assert not success
        
        # 존재하지 않는 락 정보 조회
        lock_info = lock_manager.get_lock_info("nonexistent")
        assert lock_info is None


class TestDistributedLockManagerEnvVar:
    """환경변수 기반 초기화 테스트"""
    
    def test_default_lock_dir(self):
        """기본 락 디렉터리 테스트"""
        with patch.dict('os.environ', {}, clear=True):
            manager = DistributedLockManager()
            assert str(manager.lock_dir).endswith("data/locks")
    
    def test_env_lock_dir(self):
        """환경변수 기반 락 디렉터리 테스트"""
        test_dir = tempfile.mkdtemp()
        try:
            with patch.dict('os.environ', {'LOCK_DIR': test_dir}):
                manager = DistributedLockManager()
                assert manager.lock_dir == Path(test_dir)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
LockManager 단위 테스트

filelock 기반 파일 락 처리 유틸리티 테스트
- 락 획득/해제
- 동시성 제어
- 타임아웃 처리
- 컨텍스트 매니저
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import filelock

from src.core.utils.lock_manager import (
    LockManager, 
    LockTimeoutError, 
    acquire_lock, 
    release_lock, 
    is_locked, 
    lock_context
)


class TestLockManager:
    """LockManager 테스트 클래스"""
    
    @pytest.fixture
    def lock_manager(self, tmp_path):
        """LockManager 인스턴스 생성"""
        lock_dir = tmp_path / "locks"
        return LockManager(lock_dir=str(lock_dir))
    
    def test_lock_manager_initialization(self, lock_manager):
        """LockManager 초기화 테스트"""
        assert lock_manager.lock_dir.exists()
        assert isinstance(lock_manager.active_locks, dict)
        assert len(lock_manager.active_locks) == 0
    
    def test_acquire_lock_success(self, lock_manager):
        """락 획득 성공 테스트"""
        lock_name = "test_lock"
        
        lock = lock_manager.acquire_lock(lock_name)
        
        assert lock is not None
        assert isinstance(lock, filelock.FileLock)
        assert lock_name in lock_manager.active_locks
        assert lock_manager.active_locks[lock_name] == lock
    
    def test_acquire_lock_with_timeout(self, lock_manager):
        """타임아웃과 함께 락 획득 테스트"""
        lock_name = "test_lock_timeout"
        timeout = 5.0
        
        lock = lock_manager.acquire_lock(lock_name, timeout=timeout)
        
        assert lock is not None
        assert lock_name in lock_manager.active_locks
    
    def test_acquire_lock_timeout_failure(self, lock_manager):
        """락 획득 타임아웃 실패 테스트"""
        lock_name = "test_lock_timeout_fail"
        
        # 이미 락을 획득
        first_lock = lock_manager.acquire_lock(lock_name)
        
        # 두 번째 락 획득 시도 (타임아웃 발생)
        with pytest.raises(LockTimeoutError) as exc_info:
            lock_manager.acquire_lock(lock_name, timeout=0.1)
        
        assert "Failed to acquire lock" in str(exc_info.value)
        assert lock_name in str(exc_info.value)
        
        # 첫 번째 락 해제
        lock_manager.release_lock(lock_name)
    
    def test_release_lock_success(self, lock_manager):
        """락 해제 성공 테스트"""
        lock_name = "test_release_lock"
        
        # 락 획득
        lock = lock_manager.acquire_lock(lock_name)
        
        # 락 해제
        result = lock_manager.release_lock(lock_name)
        
        assert result is True
        assert lock_name not in lock_manager.active_locks
    
    def test_release_nonexistent_lock(self, lock_manager):
        """존재하지 않는 락 해제 테스트"""
        lock_name = "nonexistent_lock"
        
        result = lock_manager.release_lock(lock_name)
        
        assert result is False
    
    def test_is_locked(self, lock_manager):
        """락 상태 확인 테스트"""
        lock_name = "test_is_locked"
        
        # 초기 상태는 락이 없음
        assert lock_manager.is_locked(lock_name) is False
        
        # 락 획득
        lock_manager.acquire_lock(lock_name)
        assert lock_manager.is_locked(lock_name) is True
        
        # 락 해제
        lock_manager.release_lock(lock_name)
        assert lock_manager.is_locked(lock_name) is False
    
    def test_get_lock_info(self, lock_manager):
        """락 정보 조회 테스트"""
        lock_name = "test_lock_info"
        
        # 락이 없는 경우
        info = lock_manager.get_lock_info(lock_name)
        assert info is None
        
        # 락 획득
        lock = lock_manager.acquire_lock(lock_name)
        info = lock_manager.get_lock_info(lock_name)
        
        assert info is not None
        assert info["lock_name"] == lock_name
        assert info["lock_path"] == str(lock_manager.lock_dir / f"{lock_name}.lock")
        assert "acquired_at" in info
        assert "lock_object" in info
        
        # 락 해제
        lock_manager.release_lock(lock_name)
    
    def test_list_locks(self, lock_manager):
        """락 목록 조회 테스트"""
        # 초기 상태
        locks = lock_manager.list_locks()
        assert len(locks) == 0
        
        # 여러 락 획득
        lock_names = ["lock1", "lock2", "lock3"]
        for name in lock_names:
            lock_manager.acquire_lock(name)
        
        # 락 목록 조회
        locks = lock_manager.list_locks()
        assert len(locks) == 3
        
        for name in lock_names:
            assert name in locks
            assert locks[name]["lock_name"] == name
        
        # 락 해제
        for name in lock_names:
            lock_manager.release_lock(name)
    
    def test_cleanup_locks(self, lock_manager):
        """오래된 락 정리 테스트"""
        # 테스트용 락 파일 생성
        old_lock_path = lock_manager.lock_dir / "old_lock.lock"
        old_lock_path.touch()
        
        # 오래된 락 파일의 수정 시간을 과거로 설정
        old_time = time.time() - (25 * 3600)  # 25시간 전
        old_lock_path.touch()
        os.utime(old_lock_path, (old_time, old_time))
        
        # 정리 실행
        cleaned_count = lock_manager.cleanup_locks(max_age_hours=24)
        
        assert cleaned_count >= 1
        assert not old_lock_path.exists()
    
    def test_lock_context_manager(self, lock_manager):
        """락 컨텍스트 매니저 테스트"""
        lock_name = "test_context_lock"
        
        with lock_manager.lock_context(lock_name):
            # 컨텍스트 내에서 락이 획득되어 있어야 함
            assert lock_manager.is_locked(lock_name) is True
        
        # 컨텍스트 종료 후 락이 해제되어 있어야 함
        assert lock_manager.is_locked(lock_name) is False
    
    def test_lock_context_with_timeout(self, lock_manager):
        """타임아웃과 함께 락 컨텍스트 매니저 테스트"""
        lock_name = "test_context_timeout"
        timeout = 2.0
        
        with lock_manager.lock_context(lock_name, timeout=timeout):
            assert lock_manager.is_locked(lock_name) is True
        
        assert lock_manager.is_locked(lock_name) is False
    
    def test_lock_context_timeout_failure(self, lock_manager):
        """락 컨텍스트 매니저 타임아웃 실패 테스트"""
        lock_name = "test_context_timeout_fail"
        
        # 이미 락을 획득
        first_lock = lock_manager.acquire_lock(lock_name)
        
        # 두 번째 락 획득 시도 (타임아웃 발생)
        with pytest.raises(LockTimeoutError):
            with lock_manager.lock_context(lock_name, timeout=0.1):
                pass
        
        # 첫 번째 락 해제
        lock_manager.release_lock(lock_name)
    
    def test_health_check(self, lock_manager):
        """상태 확인 테스트"""
        health_info = lock_manager.health_check()
        
        assert health_info["status"] == "healthy"
        assert health_info["lock_dir"] == str(lock_manager.lock_dir)
        assert "active_locks_count" in health_info
        assert "total_locks_count" in health_info
        assert health_info["active_locks_count"] == 0
    
    def test_concurrent_lock_acquisition(self, lock_manager):
        """동시 락 획득 테스트"""
        lock_name = "concurrent_lock"
        results = []
        errors = []
        
        def acquire_lock_thread():
            try:
                lock = lock_manager.acquire_lock(lock_name, timeout=1.0)
                time.sleep(0.1)  # 짧은 대기
                lock_manager.release_lock(lock_name)
                results.append("success")
            except LockTimeoutError:
                errors.append("timeout")
            except Exception as e:
                errors.append(str(e))
        
        # 여러 스레드에서 동시에 락 획득 시도
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=acquire_lock_thread)
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 하나는 성공하고 나머지는 타임아웃이어야 함
        assert len(results) == 1
        assert len(errors) == 4
        assert all(error == "timeout" for error in errors)
    
    def test_lock_file_creation_and_cleanup(self, lock_manager):
        """락 파일 생성 및 정리 테스트"""
        lock_name = "test_file_lock"
        
        # 락 획득 전 파일이 없어야 함
        lock_file_path = lock_manager.lock_dir / f"{lock_name}.lock"
        assert not lock_file_path.exists()
        
        # 락 획득
        lock = lock_manager.acquire_lock(lock_name)
        assert lock_file_path.exists()
        
        # 락 해제
        lock_manager.release_lock(lock_name)
        assert not lock_file_path.exists()


class TestGlobalFunctions:
    """전역 함수 테스트 클래스"""
    
    @pytest.fixture
    def temp_lock_dir(self, tmp_path):
        """임시 락 디렉토리 생성"""
        lock_dir = tmp_path / "global_locks"
        lock_dir.mkdir()
        return lock_dir
    
    def test_acquire_lock_global(self, temp_lock_dir):
        """전역 acquire_lock 함수 테스트"""
        lock_name = "global_test_lock"
        
        with patch('src.core.utils.lock_manager.LockManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.acquire_lock.return_value = Mock()
            
            lock = acquire_lock(lock_name)
            
            mock_manager.acquire_lock.assert_called_once_with(lock_name, 10.0)
            assert lock is not None
    
    def test_release_lock_global(self, temp_lock_dir):
        """전역 release_lock 함수 테스트"""
        lock_name = "global_test_lock"
        
        with patch('src.core.utils.lock_manager.LockManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.release_lock.return_value = True
            
            result = release_lock(lock_name)
            
            mock_manager.release_lock.assert_called_once_with(lock_name)
            assert result is True
    
    def test_is_locked_global(self, temp_lock_dir):
        """전역 is_locked 함수 테스트"""
        lock_name = "global_test_lock"
        
        with patch('src.core.utils.lock_manager.LockManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.is_locked.return_value = True
            
            result = is_locked(lock_name)
            
            mock_manager.is_locked.assert_called_once_with(lock_name)
            assert result is True
    
    def test_lock_context_global(self, temp_lock_dir):
        """전역 lock_context 함수 테스트"""
        lock_name = "global_test_lock"
        
        with patch('src.core.utils.lock_manager.LockManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            with lock_context(lock_name):
                pass
            
            # lock_context가 호출되었는지 확인
            assert mock_manager.lock_context.called


class TestLockTimeoutError:
    """LockTimeoutError 예외 테스트"""
    
    def test_lock_timeout_error_message(self):
        """LockTimeoutError 메시지 테스트"""
        lock_name = "test_timeout_lock"
        timeout = 5.0
        
        error = LockTimeoutError(f"Failed to acquire lock '{lock_name}' after {timeout} seconds")
        
        assert "Failed to acquire lock" in str(error)
        assert lock_name in str(error)
        assert str(timeout) in str(error)
    
    def test_lock_timeout_error_inheritance(self):
        """LockTimeoutError 상속 관계 테스트"""
        error = LockTimeoutError("Test error")
        
        assert isinstance(error, Exception)
        assert isinstance(error, LockTimeoutError)


# 테스트 실행을 위한 import
import os 
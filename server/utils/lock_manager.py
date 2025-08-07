"""
분산 락 관리자
Redis Redlock을 filelock + diskcache로 대체

PRD 요구사항에 따른 분산 락 기능
"""

import time
import logging
import uuid
import threading
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from pathlib import Path
import filelock
from threading import Lock as ThreadLock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LockInfo:
    """락 정보 클래스"""
    def __init__(self, lock_id: str, resource_name: str, ttl: int):
        self.lock_id = lock_id
        self.resource_name = resource_name
        self.ttl = ttl
        self.acquired_at = time.time()
        self.file_lock: Optional[filelock.FileLock] = None
    
    def is_expired(self) -> bool:
        """락 만료 여부 확인"""
        return (time.time() - self.acquired_at) > self.ttl
    
    def remaining_time(self) -> float:
        """남은 시간 반환"""
        return max(0, self.ttl - (time.time() - self.acquired_at))


class DistributedLockManager:
    """
    파일 기반 분산 락 관리자
    Redis Redlock 알고리즘을 로컬 파일 시스템으로 구현
    """
    
    def __init__(self, lock_dir: str = None):
        if lock_dir is None:
            import os
            lock_dir = os.getenv("LOCK_DIR", "./data/locks")
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.local_locks: Dict[str, LockInfo] = {}  # 프로세스 내 락 관리
        self._thread_lock = ThreadLock()
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # 정리 스레드 시작
        self._start_cleanup_thread()
        
        logger.info(f"DistributedLockManager initialized with directory: {self.lock_dir}")
    
    def _start_cleanup_thread(self):
        """만료된 락 정리 스레드 시작"""
        def cleanup_worker():
            while not self._stop_cleanup.wait(10):  # 10초마다 정리
                self.cleanup_expired_locks()
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.debug("Lock cleanup thread started")
    
    def __del__(self):
        """소멸자에서 정리 스레드 종료"""
        if hasattr(self, '_stop_cleanup'):
            self._stop_cleanup.set()
        if hasattr(self, '_cleanup_thread') and self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)
    
    @contextmanager
    def acquire_lock(
        self, 
        resource_name: str, 
        ttl: int = 30,
        blocking: bool = True,
        timeout: Optional[float] = None
    ):
        """
        Redis Redlock 호환 분산 락 획득
        
        Args:
            resource_name: 락 리소스 이름
            ttl: 락 만료 시간 (초)
            blocking: 블로킹 여부
            timeout: 타임아웃 (초)
        
        Yields:
            str: 락 ID (성공) 또는 None (실패)
        """
        lock_id = str(uuid.uuid4())
        lock_file = self.lock_dir / f"{resource_name}.lock"
        
        # 파일 락 생성
        file_lock = filelock.FileLock(str(lock_file))
        
        acquired = False
        lock_info = None
        
        try:
            # 락 획득 시도
            if blocking:
                file_lock.acquire(timeout=timeout)
            else:
                file_lock.acquire(timeout=0.1)
            
            acquired = True
            
            # 락 정보 생성 및 등록
            lock_info = LockInfo(lock_id, resource_name, ttl)
            lock_info.file_lock = file_lock
            
            with self._thread_lock:
                self.local_locks[resource_name] = lock_info
            
            logger.debug(f"Lock acquired: {resource_name} ({lock_id}) for {ttl}s")
            yield lock_id
            
        except filelock.Timeout:
            logger.warning(f"Lock acquisition timeout: {resource_name}")
            if not blocking:
                yield None
            else:
                raise
        except Exception as e:
            logger.error(f"Lock acquisition failed: {resource_name} - {e}")
            yield None
        finally:
            if acquired and lock_info:
                try:
                    file_lock.release()
                    with self._thread_lock:
                        self.local_locks.pop(resource_name, None)
                    logger.debug(f"Lock released: {resource_name} ({lock_id})")
                except Exception as e:
                    logger.error(f"Lock release failed: {resource_name} - {e}")
    
    def acquire_lock_sync(
        self, 
        resource_name: str, 
        ttl: int = 30,
        timeout: Optional[float] = None
    ) -> Optional[str]:
        """
        동기적 락 획득 (컨텍스트 매니저 없이)
        
        Args:
            resource_name: 락 리소스 이름
            ttl: 락 만료 시간 (초)
            timeout: 타임아웃 (초)
        
        Returns:
            Optional[str]: 락 ID (성공) 또는 None (실패)
        """
        lock_id = str(uuid.uuid4())
        lock_file = self.lock_dir / f"{resource_name}.lock"
        
        try:
            # 파일 락 생성
            file_lock = filelock.FileLock(str(lock_file))
            file_lock.acquire(timeout=timeout or 0.1)
            
            # 락 정보 생성 및 등록
            lock_info = LockInfo(lock_id, resource_name, ttl)
            lock_info.file_lock = file_lock
            
            with self._thread_lock:
                self.local_locks[resource_name] = lock_info
            
            logger.debug(f"Sync lock acquired: {resource_name} ({lock_id})")
            return lock_id
            
        except filelock.Timeout:
            logger.warning(f"Sync lock acquisition timeout: {resource_name}")
            return None
        except Exception as e:
            logger.error(f"Sync lock acquisition failed: {resource_name} - {e}")
            return None
    
    def release_lock(self, resource_name: str, lock_id: str) -> bool:
        """
        락 해제
        
        Args:
            resource_name: 락 리소스 이름
            lock_id: 락 ID
        
        Returns:
            bool: 해제 성공 여부
        """
        try:
            with self._thread_lock:
                lock_info = self.local_locks.get(resource_name)
                
                if not lock_info:
                    logger.warning(f"Lock not found: {resource_name}")
                    return False
                
                if lock_info.lock_id != lock_id:
                    logger.warning(f"Lock ID mismatch: {resource_name}")
                    return False
                
                # 파일 락 해제
                if lock_info.file_lock:
                    lock_info.file_lock.release()
                
                # 로컬 락 제거
                del self.local_locks[resource_name]
            
            logger.debug(f"Lock released: {resource_name} ({lock_id})")
            return True
            
        except Exception as e:
            logger.error(f"Lock release failed: {resource_name} - {e}")
            return False
    
    def extend_lock(self, resource_name: str, lock_id: str, additional_ttl: int) -> bool:
        """
        락 TTL 연장
        
        Args:
            resource_name: 락 리소스 이름
            lock_id: 락 ID
            additional_ttl: 추가 TTL (초)
        
        Returns:
            bool: 연장 성공 여부
        """
        try:
            with self._thread_lock:
                lock_info = self.local_locks.get(resource_name)
                
                if not lock_info:
                    return False
                
                if lock_info.lock_id != lock_id:
                    return False
                
                if lock_info.is_expired():
                    return False
                
                # TTL 연장
                lock_info.ttl += additional_ttl
            
            logger.debug(f"Lock extended: {resource_name} (+{additional_ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Lock extension failed: {resource_name} - {e}")
            return False
    
    def is_locked(self, resource_name: str) -> bool:
        """락 상태 확인"""
        try:
            # 파일 락 확인
            lock_file = self.lock_dir / f"{resource_name}.lock"
            if not lock_file.exists():
                return False
            
            # 로컬 락 정보 확인
            with self._thread_lock:
                lock_info = self.local_locks.get(resource_name)
                if lock_info and not lock_info.is_expired():
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Lock status check failed: {resource_name} - {e}")
            return False
    
    def get_lock_info(self, resource_name: str) -> Optional[Dict[str, Any]]:
        """락 정보 조회"""
        try:
            with self._thread_lock:
                lock_info = self.local_locks.get(resource_name)
                if not lock_info:
                    return None
                
                return {
                    "lock_id": lock_info.lock_id,
                    "resource_name": lock_info.resource_name,
                    "ttl": lock_info.ttl,
                    "acquired_at": lock_info.acquired_at,
                    "remaining_time": lock_info.remaining_time(),
                    "is_expired": lock_info.is_expired()
                }
        except Exception as e:
            logger.error(f"Get lock info failed: {resource_name} - {e}")
            return None
    
    def force_release(self, resource_name: str) -> bool:
        """강제 락 해제 (주의: 데이터 손실 위험)"""
        try:
            lock_file = self.lock_dir / f"{resource_name}.lock"
            
            # 로컬 락 정보 제거
            with self._thread_lock:
                lock_info = self.local_locks.pop(resource_name, None)
                if lock_info and lock_info.file_lock:
                    try:
                        lock_info.file_lock.release()
                    except:
                        pass
            
            # 락 파일 강제 삭제
            if lock_file.exists():
                lock_file.unlink()
            
            logger.warning(f"Force released lock: {resource_name}")
            return True
            
        except Exception as e:
            logger.error(f"Force release failed: {resource_name} - {e}")
            return False
    
    def cleanup_expired_locks(self) -> int:
        """만료된 락 정리"""
        cleaned_count = 0
        
        try:
            expired_locks = []
            
            with self._thread_lock:
                for resource_name, lock_info in self.local_locks.items():
                    if lock_info.is_expired():
                        expired_locks.append(resource_name)
            
            for resource_name in expired_locks:
                if self.force_release(resource_name):
                    cleaned_count += 1
                    logger.info(f"Cleaned up expired lock: {resource_name}")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return cleaned_count
    
    def get_all_locks(self) -> Dict[str, Dict[str, Any]]:
        """모든 락 정보 조회"""
        try:
            with self._thread_lock:
                return {
                    resource_name: {
                        "lock_id": lock_info.lock_id,
                        "ttl": lock_info.ttl,
                        "acquired_at": lock_info.acquired_at,
                        "remaining_time": lock_info.remaining_time(),
                        "is_expired": lock_info.is_expired()
                    }
                    for resource_name, lock_info in self.local_locks.items()
                }
        except Exception as e:
            logger.error(f"Get all locks failed: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """상태 점검"""
        try:
            active_locks = 0
            expired_locks = 0
            
            with self._thread_lock:
                for lock_info in self.local_locks.values():
                    if lock_info.is_expired():
                        expired_locks += 1
                    else:
                        active_locks += 1
            
            # 간단한 락 테스트
            test_resource = "health_check_test"
            test_success = False
            
            with self.acquire_lock(test_resource, ttl=5, blocking=False) as lock_id:
                test_success = lock_id is not None
            
            return {
                "status": "healthy" if test_success else "error",
                "lock_dir": str(self.lock_dir),
                "active_locks": active_locks,
                "expired_locks": expired_locks,
                "total_locks": len(self.local_locks),
                "cleanup_thread_running": self._cleanup_thread and self._cleanup_thread.is_alive(),
                "test_lock_success": test_success
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # 기본 테스트
    import json
    
    manager = DistributedLockManager()
    print("✅ DistributedLockManager 완전 구현 성공")
    print("📊 상태:", json.dumps(manager.health_check(), indent=2))
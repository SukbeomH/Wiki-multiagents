"""
파일 락 처리 유틸리티

filelock 라이브러리 기반의 기본 파일 락 획득/해제 유틸리티
- 타임아웃 처리
- 사용자 정의 예외
- 동시성 제어

단순화 계획에 맞춘 분산 락 매니저(DistributedLockManager) 호환 래퍼를 포함합니다.
기존 테스트들에서 `DistributedLockManager`와 `LockInfo`를 기대하므로, 해당 API를 제공하여
파일 기반 락으로 동작하도록 합니다.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

import filelock

logger = logging.getLogger(__name__)


class LockTimeoutError(Exception):
    """락 획득 타임아웃 예외"""
    pass


class LockInfo:
    """분산 락 메타데이터(테스트 호환용)"""

    def __init__(self, lock_id: str, resource_name: str, ttl: int, file_lock: Optional[filelock.FileLock] = None):
        self.lock_id = lock_id
        self.resource_name = resource_name
        self.ttl = int(ttl)
        self.acquired_at = time.time()
        self.file_lock = file_lock

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return True
        return time.time() >= (self.acquired_at + self.ttl)

    def remaining_time(self) -> int:
        if self.ttl <= 0:
            return 0
        remaining = int((self.acquired_at + self.ttl) - time.time())
        return remaining if remaining > 0 else 0


class LockManager:
    """파일 락 관리자"""
    
    def __init__(self, lock_dir: Optional[str] = None):
        """
        LockManager 초기화
        
        Args:
            lock_dir: 락 파일 저장 디렉토리
        """
        self.lock_dir = Path(lock_dir) if lock_dir else Path("data/locks")
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # 활성 락 추적
        self.active_locks: Dict[str, filelock.FileLock] = {}
        
        logger.info(f"LockManager initialized with lock dir: {self.lock_dir}")
    
    def acquire_lock(self, lock_name: str, timeout: float = 10.0) -> filelock.FileLock:
        """
        락 획득
        
        Args:
            lock_name: 락 이름
            timeout: 타임아웃 시간 (초)
            
        Returns:
            filelock.FileLock: 획득된 락 객체
            
        Raises:
            LockTimeoutError: 타임아웃 발생 시
        """
        try:
            lock_path = self.lock_dir / f"{lock_name}.lock"
            lock = filelock.FileLock(str(lock_path), timeout=timeout)
            
            logger.info(f"Attempting to acquire lock: {lock_name}")
            lock.acquire()
            
            # 활성 락에 추가
            self.active_locks[lock_name] = lock
            
            logger.info(f"Lock acquired successfully: {lock_name}")
            return lock
            
        except filelock.Timeout as e:
            logger.error(f"Lock acquisition timeout: {lock_name} after {timeout}s")
            raise LockTimeoutError(f"Failed to acquire lock '{lock_name}' after {timeout} seconds") from e
        except Exception as e:
            logger.error(f"Lock acquisition failed: {lock_name} - {e}")
            raise
    
    def release_lock(self, lock_name: str) -> bool:
        """
        락 해제
        
        Args:
            lock_name: 락 이름
            
        Returns:
            bool: 해제 성공 여부
        """
        try:
            if lock_name in self.active_locks:
                lock = self.active_locks[lock_name]
                lock.release()
                del self.active_locks[lock_name]
                
                logger.info(f"Lock released successfully: {lock_name}")
                return True
            else:
                logger.warning(f"Lock not found in active locks: {lock_name}")
                return False
                
        except Exception as e:
            logger.error(f"Lock release failed: {lock_name} - {e}")
            return False
    
    def is_locked(self, lock_name: str) -> bool:
        """
        락 상태 확인
        
        Args:
            lock_name: 락 이름
            
        Returns:
            bool: 락 상태 (True: 잠김, False: 해제됨)
        """
        try:
            lock_path = self.lock_dir / f"{lock_name}.lock"
            lock = filelock.FileLock(str(lock_path), timeout=0)
            
            # 즉시 락 시도 (타임아웃 0)
            try:
                lock.acquire()
                lock.release()
                return False  # 락 획득 성공 = 잠기지 않음
            except filelock.Timeout:
                return True  # 락 획득 실패 = 잠김
                
        except Exception as e:
            logger.error(f"Lock status check failed: {lock_name} - {e}")
            return False
    
    def get_lock_info(self, lock_name: str) -> Optional[Dict[str, Any]]:
        """
        락 정보 조회
        
        Args:
            lock_name: 락 이름
            
        Returns:
            Optional[Dict[str, Any]]: 락 정보
        """
        try:
            lock_path = self.lock_dir / f"{lock_name}.lock"
            
            if not lock_path.exists():
                return None
            
            # 파일 정보 조회
            stat = lock_path.stat()
            
            return {
                "lock_name": lock_name,
                "lock_path": str(lock_path),
                "exists": True,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_active": lock_name in self.active_locks
            }
            
        except Exception as e:
            logger.error(f"Failed to get lock info: {lock_name} - {e}")
            return None
    
    def list_locks(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 락 목록 조회
        
        Returns:
            Dict[str, Dict[str, Any]]: 락 목록
        """
        locks = {}
        
        try:
            for lock_file in self.lock_dir.glob("*.lock"):
                lock_name = lock_file.stem  # .lock 확장자 제거
                lock_info = self.get_lock_info(lock_name)
                if lock_info:
                    locks[lock_name] = lock_info
                    
        except Exception as e:
            logger.error(f"Failed to list locks: {e}")
        
        return locks
    
    def cleanup_locks(self, max_age_hours: int = 24) -> int:
        """
        오래된 락 파일 정리
        
        Args:
            max_age_hours: 최대 보관 시간 (시간)
            
        Returns:
            int: 정리된 락 파일 수
        """
        try:
            cutoff_time = time.time() - (max_age_hours * 3600)
            cleaned_count = 0
            
            for lock_file in self.lock_dir.glob("*.lock"):
                try:
                    if lock_file.stat().st_mtime < cutoff_time:
                        lock_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up old lock file: {lock_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup lock file {lock_file.name}: {e}")
            
            logger.info(f"Lock cleanup completed: {cleaned_count} files removed")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Lock cleanup failed: {e}")
            return 0
    
    @contextmanager
    def lock_context(self, lock_name: str, timeout: float = 10.0):
        """
        컨텍스트 매니저를 사용한 락 처리
        
        Args:
            lock_name: 락 이름
            timeout: 타임아웃 시간 (초)
            
        Yields:
            filelock.FileLock: 획득된 락 객체
        """
        lock = None
        try:
            lock = self.acquire_lock(lock_name, timeout)
            yield lock
        finally:
            if lock:
                self.release_lock(lock_name)
    
    def health_check(self) -> Dict[str, Any]:
        """
        LockManager 상태 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            health_info = {
                "status": "healthy",
                "lock_dir": str(self.lock_dir),
                "active_locks_count": len(self.active_locks),
                "active_locks": list(self.active_locks.keys()),
                "total_locks": len(list(self.lock_dir.glob("*.lock"))),
                "timestamp": time.time()
            }
            
            logger.info("LockManager health check completed")
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
            
            logger.error(f"LockManager health check failed: {e}")
            return health_info


# 전역 LockManager 인스턴스
lock_manager = LockManager()


def acquire_lock(lock_name: str, timeout: float = 10.0) -> filelock.FileLock:
    """
    전역 락 획득 함수
    
    Args:
        lock_name: 락 이름
        timeout: 타임아웃 시간 (초)
        
    Returns:
        filelock.FileLock: 획득된 락 객체
    """
    return lock_manager.acquire_lock(lock_name, timeout)


def release_lock(lock_name: str) -> bool:
    """
    전역 락 해제 함수
    
    Args:
        lock_name: 락 이름
        
    Returns:
        bool: 해제 성공 여부
    """
    return lock_manager.release_lock(lock_name)


def is_locked(lock_name: str) -> bool:
    """
    전역 락 상태 확인 함수
    
    Args:
        lock_name: 락 이름
        
    Returns:
        bool: 락 상태
    """
    return lock_manager.is_locked(lock_name)


@contextmanager
def lock_context(lock_name: str, timeout: float = 10.0):
    """
    전역 컨텍스트 매니저 락 함수
    
    Args:
        lock_name: 락 이름
        timeout: 타임아웃 시간 (초)
        
    Yields:
        filelock.FileLock: 획득된 락 객체
    """
    with lock_manager.lock_context(lock_name, timeout) as lock:
        yield lock


class DistributedLockManager:
    """filelock 기반 분산 락 매니저 (테스트 호환용 API)"""

    def __init__(self, lock_dir: Optional[str] = None):
        env_lock_dir = os.environ.get("LOCK_DIR")
        base_dir = lock_dir or env_lock_dir or "data/locks"
        self.lock_dir: Path = Path(base_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        # 리소스명 -> LockInfo
        self.local_locks: Dict[str, LockInfo] = {}
        # 테스트에서 존재 여부만 확인
        self._cleanup_thread = None  # type: ignore

        logger.info(f"DistributedLockManager initialized with lock dir: {self.lock_dir}")

    def _lock_path(self, resource_name: str) -> Path:
        return self.lock_dir / f"{resource_name}.lock"

    def _try_acquire(self, resource_name: str, timeout: float) -> Optional[filelock.FileLock]:
        lock_path = self._lock_path(resource_name)
        fl = filelock.FileLock(str(lock_path), timeout=timeout)
        try:
            fl.acquire()
            return fl
        except filelock.Timeout:
            return None

    def acquire_lock_sync(self, resource_name: str, ttl: int = 30, timeout: float = 1.0) -> Optional[str]:
        # 이미 보유한 락이 있고 만료되지 않았다면 실패 처리
        existing = self.local_locks.get(resource_name)
        if existing and not existing.is_expired():
            # 이미 잠겨있음 → 새 락 획득 실패
            return None

        fl = self._try_acquire(resource_name, timeout)
        if fl is None:
            return None

        lock_id = f"{int(time.time()*1000)}-{resource_name}"
        self.local_locks[resource_name] = LockInfo(lock_id, resource_name, ttl, fl)
        return lock_id

    def release_lock(self, resource_name: str, lock_id: str) -> bool:
        info = self.local_locks.get(resource_name)
        if not info or info.lock_id != lock_id:
            return False
        try:
            if info.file_lock:
                try:
                    info.file_lock.release()
                except Exception:
                    pass
            self.local_locks.pop(resource_name, None)
            # 락 파일 정리 (남아있을 수 있음)
            lp = self._lock_path(resource_name)
            if lp.exists():
                try:
                    lp.unlink()
                except Exception:
                    pass
            return True
        except Exception:
            return False

    def extend_lock(self, resource_name: str, lock_id: str, extra_ttl: int) -> bool:
        info = self.local_locks.get(resource_name)
        if not info or info.lock_id != lock_id:
            return False
        info.ttl += int(extra_ttl)
        return True

    def is_locked(self, resource_name: str) -> bool:
        # 우선 내부 상태 확인
        info = self.local_locks.get(resource_name)
        if info and not info.is_expired():
            return True

        # 파일 기준으로도 확인 (0초 타임아웃 시도)
        fl = filelock.FileLock(str(self._lock_path(resource_name)), timeout=0)
        try:
            fl.acquire()
            fl.release()
            return False
        except filelock.Timeout:
            return True
        except Exception:
            return False

    @contextmanager
    def acquire_lock(self, resource_name: str, ttl: int = 30, timeout: float = 1.0):
        lock_id = self.acquire_lock_sync(resource_name, ttl=ttl, timeout=timeout)
        try:
            yield lock_id
        finally:
            if lock_id:
                self.release_lock(resource_name, lock_id)

    def force_release(self, resource_name: str) -> bool:
        info = self.local_locks.get(resource_name)
        if info:
            try:
                if info.file_lock:
                    try:
                        info.file_lock.release()
                    except Exception:
                        pass
            finally:
                self.local_locks.pop(resource_name, None)

        # 파일 제거 시도
        lp = self._lock_path(resource_name)
        if lp.exists():
            try:
                lp.unlink()
                return True
            except Exception:
                return False
        return True

    def cleanup_expired_locks(self) -> int:
        cleaned = 0
        to_remove = []
        now = time.time()
        for resource, info in list(self.local_locks.items()):
            if info.ttl <= 0 or now >= (info.acquired_at + info.ttl):
                # 만료 → 해제
                try:
                    if info.file_lock:
                        try:
                            info.file_lock.release()
                        except Exception:
                            pass
                    lp = self._lock_path(resource)
                    if lp.exists():
                        try:
                            lp.unlink()
                        except Exception:
                            pass
                finally:
                    to_remove.append(resource)
                    cleaned += 1
        for r in to_remove:
            self.local_locks.pop(r, None)
        return cleaned

    def get_lock_info(self, resource_name: str) -> Optional[Dict[str, Any]]:
        info = self.local_locks.get(resource_name)
        if not info:
            # 파일만 존재하는 경우 최소 정보 제공
            lp = self._lock_path(resource_name)
            if not lp.exists():
                return None
            try:
                st = lp.stat()
                return {
                    "resource_name": resource_name,
                    "lock_path": str(lp),
                    "exists": True,
                    "size": st.st_size,
                }
            except Exception:
                return None
        return {
            "lock_id": info.lock_id,
            "resource_name": info.resource_name,
            "ttl": info.ttl,
            "acquired_at": info.acquired_at,
            "remaining": info.remaining_time(),
        }

    def get_all_locks(self) -> Dict[str, Dict[str, Any]]:
        locks: Dict[str, Dict[str, Any]] = {}
        for resource in set(list(self.local_locks.keys()) + [p.stem for p in self.lock_dir.glob("*.lock")]):
            li = self.get_lock_info(resource)
            if li:
                locks[resource] = li
        return locks

    def health_check(self) -> Dict[str, Any]:
        # 간단한 자기 진단
        test_ok = False
        try:
            rid = self.acquire_lock_sync("__health_check__", ttl=1, timeout=0.1)
            if rid:
                self.release_lock("__health_check__", rid)
                test_ok = True
        except Exception:
            test_ok = False
        expired_count = sum(1 for i in self.local_locks.values() if i.is_expired())
        return {
            "status": "healthy" if test_ok else "error",
            "lock_dir": str(self.lock_dir),
            "active_locks": len(self.local_locks),
            "expired_locks": expired_count,
            "test_lock_success": test_ok,
        }
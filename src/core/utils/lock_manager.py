"""
파일 락 처리 유틸리티

filelock 라이브러리 기반의 기본 파일 락 획득/해제 유틸리티
- 타임아웃 처리
- 사용자 정의 예외
- 동시성 제어
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

import filelock

logger = logging.getLogger(__name__)


class LockTimeoutError(Exception):
    """락 획득 타임아웃 예외"""
    pass


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
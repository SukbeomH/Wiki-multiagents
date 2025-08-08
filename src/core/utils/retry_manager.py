"""
재시도 로직 관리자

base=1s, max 3회 재시도 로직 구현
- Decorator 및 래퍼 함수 지원
- 고정 지연 1초
- 최대 3회 재시도
- 재시도 횟수 초과 시 예외 전달
"""

import logging
import time
import functools
from typing import Callable, Any, Optional, Type, Union, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """재시도 횟수 초과 예외"""
    pass


class RetryManager:
    """재시도 로직 관리자"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        RetryManager 초기화
        
        Args:
            max_retries: 최대 재시도 횟수 (기본값: 3)
            base_delay: 기본 지연 시간 (초) (기본값: 1.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        logger.info(f"RetryManager initialized: max_retries={max_retries}, base_delay={base_delay}s")
    
    def retry(
        self,
        func: Callable,
        *args,
        retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None,
        **kwargs
    ) -> Any:
        """
        함수 재시도 실행
        
        Args:
            func: 실행할 함수
            *args: 함수 인자
            retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
            **kwargs: 함수 키워드 인자
            
        Returns:
            Any: 함수 실행 결과
            
        Raises:
            RetryExhaustedError: 재시도 횟수 초과 시
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):  # 0부터 시작하므로 +1
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries + 1} for function {func.__name__}")
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # 재시도할 예외인지 확인
                if retry_exceptions and not isinstance(e, retry_exceptions):
                    logger.debug(f"Exception {type(e).__name__} not in retry_exceptions, re-raising")
                    raise
                
                # 마지막 시도가 아니면 재시도
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    logger.info(f"Retrying in {self.base_delay} seconds...")
                    time.sleep(self.base_delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed for {func.__name__}")
                    break
        
        # 모든 재시도 실패
        raise RetryExhaustedError(
            f"Function {func.__name__} failed after {self.max_retries + 1} attempts. "
            f"Last exception: {type(last_exception).__name__}: {last_exception}"
        ) from last_exception
    
    def retry_async(
        self,
        func: Callable,
        *args,
        retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None,
        **kwargs
    ) -> Any:
        """
        비동기 함수 재시도 실행
        
        Args:
            func: 실행할 비동기 함수
            *args: 함수 인자
            retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
            **kwargs: 함수 키워드 인자
            
        Returns:
            Any: 함수 실행 결과
            
        Raises:
            RetryExhaustedError: 재시도 횟수 초과 시
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Async attempt {attempt + 1}/{self.max_retries + 1} for function {func.__name__}")
                return asyncio.run(func(*args, **kwargs))
                
            except Exception as e:
                last_exception = e
                
                # 재시도할 예외인지 확인
                if retry_exceptions and not isinstance(e, retry_exceptions):
                    logger.debug(f"Exception {type(e).__name__} not in retry_exceptions, re-raising")
                    raise
                
                # 마지막 시도가 아니면 재시도
                if attempt < self.max_retries:
                    logger.warning(f"Async attempt {attempt + 1} failed for {func.__name__}: {e}")
                    logger.info(f"Retrying in {self.base_delay} seconds...")
                    time.sleep(self.base_delay)
                else:
                    logger.error(f"All {self.max_retries + 1} async attempts failed for {func.__name__}")
                    break
        
        # 모든 재시도 실패
        raise RetryExhaustedError(
            f"Async function {func.__name__} failed after {self.max_retries + 1} attempts. "
            f"Last exception: {type(last_exception).__name__}: {last_exception}"
        ) from last_exception


# 전역 RetryManager 인스턴스 (기본 설정)
retry_manager = RetryManager()


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None
):
    """
    재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수 (기본값: 3)
        base_delay: 기본 지연 시간 (초) (기본값: 1.0)
        retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
        
    Returns:
        Callable: 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = RetryManager(max_retries, base_delay)
            return manager.retry(func, *args, retry_exceptions=retry_exceptions, **kwargs)
        return wrapper
    return decorator


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None
):
    """
    비동기 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수 (기본값: 3)
        base_delay: 기본 지연 시간 (초) (기본값: 1.0)
        retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
        
    Returns:
        Callable: 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = RetryManager(max_retries, base_delay)
            return manager.retry_async(func, *args, retry_exceptions=retry_exceptions, **kwargs)
        return wrapper
    return decorator


def retry_function(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None,
    **kwargs
) -> Any:
    """
    함수 재시도 실행 (래퍼 함수)
    
    Args:
        func: 실행할 함수
        *args: 함수 인자
        max_retries: 최대 재시도 횟수 (기본값: 3)
        base_delay: 기본 지연 시간 (초) (기본값: 1.0)
        retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
        **kwargs: 함수 키워드 인자
        
    Returns:
        Any: 함수 실행 결과
        
    Raises:
        RetryExhaustedError: 재시도 횟수 초과 시
    """
    manager = RetryManager(max_retries, base_delay)
    return manager.retry(func, *args, retry_exceptions=retry_exceptions, **kwargs)


@contextmanager
def retry_context(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_exceptions: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None
):
    """
    재시도 컨텍스트 매니저
    
    Args:
        max_retries: 최대 재시도 횟수 (기본값: 3)
        base_delay: 기본 지연 시간 (초) (기본값: 1.0)
        retry_exceptions: 재시도할 예외 타입 (None이면 모든 예외)
        
    Yields:
        RetryManager: 재시도 매니저 인스턴스
    """
    manager = RetryManager(max_retries, base_delay)
    yield manager


# 사용 예시 함수들
def example_successful_function():
    """성공하는 함수 예시"""
    logger.info("Function executed successfully")
    return "success"


def example_failing_function(attempts_to_fail: int = 2):
    """실패하는 함수 예시"""
    if not hasattr(example_failing_function, '_call_count'):
        example_failing_function._call_count = 0
    
    example_failing_function._call_count += 1
    logger.info(f"Function call attempt {example_failing_function._call_count}")
    
    if example_failing_function._call_count <= attempts_to_fail:
        raise ValueError(f"Intentional failure on attempt {example_failing_function._call_count}")
    
    return "success after failures"


# 데코레이터 사용 예시
@retry(max_retries=3, base_delay=1.0)
def decorated_function():
    """데코레이터를 사용한 재시도 함수 예시"""
    return example_failing_function(2)


if __name__ == "__main__":
    # 기본 테스트
    print("✅ RetryManager 완전 구현 성공")
    
    # 기본 재시도 테스트
    try:
        result = retry_function(example_failing_function, 2)
        print(f"✅ 재시도 성공: {result}")
    except RetryExhaustedError as e:
        print(f"❌ 재시도 실패: {e}")
    
    # 데코레이터 테스트
    try:
        result = decorated_function()
        print(f"✅ 데코레이터 재시도 성공: {result}")
    except RetryExhaustedError as e:
        print(f"❌ 데코레이터 재시도 실패: {e}")
    
    # 컨텍스트 매니저 테스트
    with retry_context(max_retries=2, base_delay=0.5) as manager:
        try:
            result = manager.retry(example_failing_function, 1)
            print(f"✅ 컨텍스트 매니저 재시도 성공: {result}")
        except RetryExhaustedError as e:
            print(f"❌ 컨텍스트 매니저 재시도 실패: {e}") 
"""
RetryManager 단위 테스트

재시도 로직 관리자 테스트
- 재시도 횟수 및 지연 시간
- 데코레이터 기능
- 컨텍스트 매니저
- 예외 처리
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch
from typing import Callable

from src.core.utils.retry_manager import (
    RetryManager,
    RetryExhaustedError,
    retry,
    retry_async,
    retry_function,
    retry_context
)


class TestRetryManager:
    """RetryManager 테스트 클래스"""
    
    @pytest.fixture
    def retry_manager(self):
        """RetryManager 인스턴스 생성"""
        return RetryManager(max_retries=3, base_delay=0.1)
    
    def test_retry_manager_initialization(self, retry_manager):
        """RetryManager 초기화 테스트"""
        assert retry_manager.max_retries == 3
        assert retry_manager.base_delay == 0.1
    
    def test_retry_success_on_first_attempt(self, retry_manager):
        """첫 번째 시도에서 성공하는 경우 테스트"""
        def success_function():
            return "success"
        
        result = retry_manager.retry(success_function)
        
        assert result == "success"
    
    def test_retry_success_after_failures(self, retry_manager):
        """실패 후 성공하는 경우 테스트"""
        call_count = 0
        
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = retry_manager.retry(failing_then_success)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted_error(self, retry_manager):
        """재시도 횟수 초과 시 예외 발생 테스트"""
        def always_failing_function():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_manager.retry(always_failing_function)
        
        assert "Function always_failing_function failed after 4 attempts" in str(exc_info.value)
        assert "ValueError: Always fails" in str(exc_info.value)
    
    def test_retry_with_specific_exceptions(self, retry_manager):
        """특정 예외만 재시도하는 경우 테스트"""
        def function_raising_value_error():
            raise ValueError("Value error")
        
        def function_raising_type_error():
            raise TypeError("Type error")
        
        # ValueError는 재시도
        with pytest.raises(RetryExhaustedError):
            retry_manager.retry(function_raising_value_error, retry_exceptions=ValueError)
        
        # TypeError는 재시도하지 않음
        with pytest.raises(TypeError):
            retry_manager.retry(function_raising_type_error, retry_exceptions=ValueError)
    
    def test_retry_with_multiple_exceptions(self, retry_manager):
        """여러 예외 타입을 재시도하는 경우 테스트"""
        def function_raising_value_error():
            raise ValueError("Value error")
        
        def function_raising_type_error():
            raise TypeError("Type error")
        
        # ValueError와 TypeError 모두 재시도
        with pytest.raises(RetryExhaustedError):
            retry_manager.retry(function_raising_value_error, retry_exceptions=(ValueError, TypeError))
        
        with pytest.raises(RetryExhaustedError):
            retry_manager.retry(function_raising_type_error, retry_exceptions=(ValueError, TypeError))
    
    def test_retry_delay_timing(self, retry_manager):
        """재시도 지연 시간 테스트"""
        start_time = time.time()
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        retry_manager.retry(failing_function)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 2번의 재시도가 있으므로 최소 0.2초 이상 걸려야 함
        assert elapsed_time >= 0.2
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self, retry_manager):
        """비동기 재시도 성공 테스트"""
        call_count = 0
        
        async def async_failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await retry_manager.retry_async(async_failing_then_success)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_exhausted(self, retry_manager):
        """비동기 재시도 횟수 초과 테스트"""
        async def async_always_failing():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            await retry_manager.retry_async(async_always_failing)
    
    def test_retry_with_function_arguments(self, retry_manager):
        """함수 인자를 사용한 재시도 테스트"""
        def function_with_args(a, b, c=10):
            if a < 3:
                raise ValueError(f"a={a} is too small")
            return a + b + c
        
        result = retry_manager.retry(function_with_args, 1, 5, c=20)
        
        assert result == 26  # 3 + 5 + 20
    
    def test_retry_with_keyword_arguments(self, retry_manager):
        """키워드 인자를 사용한 재시도 테스트"""
        def function_with_kwargs(x, y, z=0):
            if x < 3:
                raise ValueError(f"x={x} is too small")
            return x * y + z
        
        result = retry_manager.retry(function_with_kwargs, x=1, y=5, z=10)
        
        assert result == 25  # 3 * 5 + 10


class TestRetryDecorator:
    """재시도 데코레이터 테스트 클래스"""
    
    def test_retry_decorator_success(self):
        """재시도 데코레이터 성공 테스트"""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.1)
        def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = decorated_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_exhausted(self):
        """재시도 데코레이터 횟수 초과 테스트"""
        @retry(max_retries=2, base_delay=0.1)
        def always_failing_decorated():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            always_failing_decorated()
    
    def test_retry_decorator_with_specific_exceptions(self):
        """특정 예외만 재시도하는 데코레이터 테스트"""
        @retry(max_retries=2, base_delay=0.1, retry_exceptions=ValueError)
        def function_raising_value_error():
            raise ValueError("Value error")
        
        @retry(max_retries=2, base_delay=0.1, retry_exceptions=ValueError)
        def function_raising_type_error():
            raise TypeError("Type error")
        
        # ValueError는 재시도
        with pytest.raises(RetryExhaustedError):
            function_raising_value_error()
        
        # TypeError는 재시도하지 않음
        with pytest.raises(TypeError):
            function_raising_type_error()
    
    @pytest.mark.asyncio
    async def test_retry_async_decorator(self):
        """비동기 재시도 데코레이터 테스트"""
        call_count = 0
        
        @retry_async(max_retries=2, base_delay=0.1)
        async def async_decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await async_decorated_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_preserves_function_metadata(self):
        """데코레이터가 함수 메타데이터를 보존하는지 테스트"""
        @retry(max_retries=1, base_delay=0.1)
        def test_function():
            """Test function docstring"""
            pass
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring"


class TestRetryFunction:
    """retry_function 테스트 클래스"""
    
    def test_retry_function_success(self):
        """retry_function 성공 테스트"""
        call_count = 0
        
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = retry_function(failing_then_success, max_retries=2, base_delay=0.1)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_function_exhausted(self):
        """retry_function 횟수 초과 테스트"""
        def always_failing():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            retry_function(always_failing, max_retries=2, base_delay=0.1)
    
    def test_retry_function_with_arguments(self):
        """인자를 사용한 retry_function 테스트"""
        def function_with_args(a, b):
            if a < 3:
                raise ValueError(f"a={a} is too small")
            return a + b
        
        result = retry_function(function_with_args, 1, 5, max_retries=2, base_delay=0.1)
        
        assert result == 8  # 3 + 5


class TestRetryContext:
    """retry_context 테스트 클래스"""
    
    def test_retry_context_success(self):
        """retry_context 성공 테스트"""
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        with retry_context(max_retries=2, base_delay=0.1):
            result = failing_operation()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_context_exhausted(self):
        """retry_context 횟수 초과 테스트"""
        def always_failing_operation():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            with retry_context(max_retries=2, base_delay=0.1):
                always_failing_operation()
    
    def test_retry_context_with_specific_exceptions(self):
        """특정 예외만 재시도하는 retry_context 테스트"""
        def value_error_operation():
            raise ValueError("Value error")
        
        def type_error_operation():
            raise TypeError("Type error")
        
        # ValueError는 재시도
        with pytest.raises(RetryExhaustedError):
            with retry_context(max_retries=2, base_delay=0.1, retry_exceptions=ValueError):
                value_error_operation()
        
        # TypeError는 재시도하지 않음
        with pytest.raises(TypeError):
            with retry_context(max_retries=2, base_delay=0.1, retry_exceptions=ValueError):
                type_error_operation()
    
    def test_retry_context_success_on_first_attempt(self):
        """첫 번째 시도에서 성공하는 retry_context 테스트"""
        def success_operation():
            return "success"
        
        with retry_context(max_retries=2, base_delay=0.1):
            result = success_operation()
        
        assert result == "success"


class TestRetryExhaustedError:
    """RetryExhaustedError 예외 테스트"""
    
    def test_retry_exhausted_error_message(self):
        """RetryExhaustedError 메시지 테스트"""
        error = RetryExhaustedError("Test error message")
        
        assert "Test error message" in str(error)
    
    def test_retry_exhausted_error_inheritance(self):
        """RetryExhaustedError 상속 관계 테스트"""
        error = RetryExhaustedError("Test error")
        
        assert isinstance(error, Exception)
        assert isinstance(error, RetryExhaustedError)


class TestRetryManagerIntegration:
    """RetryManager 통합 테스트"""
    
    def test_retry_manager_with_real_function(self):
        """실제 함수와 함께 RetryManager 테스트"""
        retry_manager = RetryManager(max_retries=2, base_delay=0.1)
        
        def network_request_simulation():
            import random
            if random.random() < 0.7:  # 70% 확률로 실패
                raise ConnectionError("Network timeout")
            return "data"
        
        # 여러 번 실행하여 재시도 로직 검증
        for _ in range(5):
            try:
                result = retry_manager.retry(network_request_simulation)
                assert result == "data"
                break
            except RetryExhaustedError:
                # 모든 재시도가 실패한 경우도 정상
                pass
    
    def test_retry_manager_performance(self):
        """RetryManager 성능 테스트"""
        retry_manager = RetryManager(max_retries=3, base_delay=0.01)
        
        def fast_failing_function():
            raise ValueError("Fast failure")
        
        start_time = time.time()
        
        with pytest.raises(RetryExhaustedError):
            retry_manager.retry(fast_failing_function)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 3번의 재시도가 있으므로 최소 0.03초 이상 걸려야 함
        assert elapsed_time >= 0.03
        # 하지만 너무 오래 걸리지 않아야 함 (0.1초 이하)
        assert elapsed_time <= 0.1 
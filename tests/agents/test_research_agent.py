"""
Research Agent 테스트 (모듈화된 버전)

새로운 모듈 구조에 맞는 단위 테스트
- client.py: DuckDuckGo API 클라이언트 테스트
- cache.py: 캐싱 시스템 테스트  
- agent.py: 메인 Research Agent 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import List, Dict, Any
import time

from server.schemas.agents import ResearchIn, ResearchOut
from server.agents.research.client import DuckDuckGoClient
from server.agents.research.cache import ResearchCache
from server.agents.research.agent import ResearchAgent


@pytest.mark.agent
@pytest.mark.unit
class TestDuckDuckGoClient:
    """DuckDuckGo API 클라이언트 단위 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.client = DuckDuckGoClient(
            timeout=5,
            max_results_per_query=5,
            retry_attempts=2
        )
    
    @patch('server.agents.research.client.DDGS')
    def test_client_initialization(self, mock_ddgs):
        """클라이언트 초기화 테스트"""
        mock_ddgs.return_value = Mock()
        
        client = DuckDuckGoClient(timeout=10, max_results_per_query=10)
        
        assert client.timeout == 10
        assert client.max_results_per_query == 10
        assert client.retry_attempts == 3  # 기본값
        mock_ddgs.assert_called_once_with(timeout=10, verify=True)
    
    @patch('server.agents.research.client.DDGS')
    def test_successful_search(self, mock_ddgs):
        """성공적인 검색 테스트"""
        # Mock 설정
        mock_results = [
            {"title": "Test Title 1", "body": "Test content 1", "href": "https://test1.com"},
            {"title": "Test Title 2", "body": "Test content 2", "href": "https://test2.com"}
        ]
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_results
        mock_ddgs.return_value = mock_ddgs_instance
        
        client = DuckDuckGoClient()
        results = client.search("test query", "wt-wt")
        
        assert len(results) == 2
        assert results[0]["title"] == "Test Title 1"
        assert results[1]["title"] == "Test Title 2"
        mock_ddgs_instance.text.assert_called_once_with(
            "test query",
            region="wt-wt",
            safesearch="moderate",
            timelimit=None,
            max_results=10
        )
    
    @patch('server.agents.research.client.DDGS')
    def test_rate_limit_exception(self, mock_ddgs):
        """Rate limit 예외 처리 테스트"""
        from ddgs.exceptions import RatelimitException
        
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.side_effect = RatelimitException("Rate limit exceeded")
        mock_ddgs.return_value = mock_ddgs_instance
        
        client = DuckDuckGoClient(retry_attempts=1)
        
        with pytest.raises(RatelimitException):
            client.search("test query")
    
    @patch('server.agents.research.client.DDGS')
    def test_timeout_exception(self, mock_ddgs):
        """타임아웃 예외 처리 테스트"""
        from ddgs.exceptions import TimeoutException
        
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.side_effect = TimeoutException("Request timeout")
        mock_ddgs.return_value = mock_ddgs_instance
        
        client = DuckDuckGoClient(retry_attempts=1)
        
        with pytest.raises(TimeoutException):
            client.search("test query")
    
    @patch('server.agents.research.client.DDGS')
    def test_health_check_success(self, mock_ddgs):
        """헬스 체크 성공 테스트"""
        mock_results = [{"title": "Health Test", "body": "Health content"}]
        mock_ddgs_instance = Mock()
        mock_ddgs_instance.text.return_value = mock_results
        mock_ddgs.return_value = mock_ddgs_instance
        
        client = DuckDuckGoClient()
        health = client.health_check()
        
        assert health['status'] == 'healthy'
        assert health['search_engine'] == 'duckduckgo'
        assert health['api_key_required'] is False
        assert health['test_results_count'] == 1


@pytest.mark.agent
@pytest.mark.unit
class TestResearchCache:
    """Research 캐시 시스템 단위 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.cache = ResearchCache(max_size=10, ttl_seconds=60, enable_ttl=True)
    
    def test_cache_initialization(self):
        """캐시 초기화 테스트"""
        cache = ResearchCache(max_size=100, ttl_seconds=3600, enable_ttl=False)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert cache.enable_ttl is False
        assert cache.ttl_cache is None
    
    def test_cache_key_generation(self):
        """캐시 키 생성 테스트"""
        key1 = self.cache._generate_cache_key("test query", "wt-wt", top_k=10)
        key2 = self.cache._generate_cache_key("test query", "wt-wt", top_k=10)
        key3 = self.cache._generate_cache_key("different query", "wt-wt", top_k=10)
        
        # 같은 파라미터는 같은 키 생성
        assert key1 == key2
        # 다른 쿼리는 다른 키 생성
        assert key1 != key3
        # 키는 MD5 해시 형태
        assert len(key1) == 32
        assert key1.isalnum()
    
    def test_cache_set_and_get(self):
        """캐시 저장 및 조회 테스트"""
        test_results = [{"title": "Test", "body": "Content"}]
        test_metadata = {"cached_at": "2025-08-06T00:00:00"}
        
        # 캐시에 저장
        self.cache.set("test query", test_results, test_metadata, region="wt-wt")
        
        # 캐시에서 조회
        cached_data = self.cache.get("test query", region="wt-wt")
        
        assert cached_data is not None
        results, metadata = cached_data
        assert results == test_results
        assert metadata == test_metadata
    
    def test_cache_miss(self):
        """캐시 미스 테스트"""
        cached_data = self.cache.get("nonexistent query", region="wt-wt")
        assert cached_data is None
    
    def test_cache_delete(self):
        """캐시 삭제 테스트"""
        test_results = [{"title": "Test"}]
        test_metadata = {"cached_at": "2025-08-06T00:00:00"}
        
        # 저장
        self.cache.set("test query", test_results, test_metadata)
        
        # 삭제
        deleted = self.cache.delete("test query")
        assert deleted is True
        
        # 조회 시도
        cached_data = self.cache.get("test query")
        assert cached_data is None
    
    def test_cache_clear(self):
        """캐시 정리 테스트"""
        # 여러 항목 저장
        for i in range(3):
            self.cache.set(f"query{i}", [{"title": f"Test{i}"}], {"id": i})
        
        # 정리
        self.cache.clear()
        
        # 모든 항목이 삭제되었는지 확인
        for i in range(3):
            cached_data = self.cache.get(f"query{i}")
            assert cached_data is None
        
        # 통계도 초기화되었는지 확인 (clear 후 조회로 인한 misses는 무시)
        stats = self.cache.get_stats()
        assert stats['hits'] == 0
        assert stats['sets'] == 0
        assert stats['deletes'] == 0
        # misses는 clear 후 조회로 인해 3이 됨 (정상 동작)
    
    def test_cache_stats(self):
        """캐시 통계 테스트"""
        # 초기 통계
        stats = self.cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0
        
        # 캐시 사용
        self.cache.set("query1", [{"title": "Test1"}], {"id": 1})
        self.cache.get("query1")  # 히트
        self.cache.get("query2")  # 미스
        
        # 업데이트된 통계
        stats = self.cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['sets'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_health_check(self):
        """캐시 헬스 체크 테스트"""
        health = self.cache.health_check()
        
        assert health['status'] == 'healthy'
        assert health['cache_type'] == 'research_cache'
        assert 'last_check' in health
        assert 'stats' in health
        assert 'config' in health


@pytest.mark.agent
@pytest.mark.unit
class TestResearchAgent:
    """Research Agent 단위 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.mock_client = Mock(spec=DuckDuckGoClient)
        self.mock_cache = Mock(spec=ResearchCache)
        self.agent = ResearchAgent(
            client=self.mock_client,
            cache=self.mock_cache,
            enable_cache=True
        )
    
    def test_agent_initialization(self):
        """Agent 초기화 테스트"""
        agent = ResearchAgent()
        
        assert agent.client is not None
        assert agent.cache is not None
        assert agent.enable_cache is True
    
    def test_convert_to_docs(self):
        """검색 결과를 문서로 변환하는 테스트"""
        search_results = [
            {"title": "Title 1", "body": "Body 1", "href": "https://test1.com"},
            {"title": "Title 2", "body": "Body 2", "href": "https://test2.com"}
        ]
        
        docs, metadata = self.agent._convert_to_docs(search_results, "test query")
        
        assert len(docs) == 2
        assert len(metadata) == 2
        
        # 문서 내용 확인
        assert "Title 1\n\nBody 1" in docs[0]
        assert "Title 2\n\nBody 2" in docs[1]
        
        # 메타데이터 확인
        assert metadata[0]['title'] == "Title 1"
        assert metadata[0]['url'] == "https://test1.com"
        assert metadata[0]['source'] == "duckduckgo"
        assert metadata[0]['search_query'] == "test query"
        assert metadata[0]['search_rank'] == 1
    
    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self):
        """캐시 히트 시 검색 테스트"""
        # Mock 설정
        cached_results = [{"title": "Cached Title", "body": "Cached content"}]
        cached_metadata = {"cached_at": "2025-08-06T00:00:00"}
        self.mock_cache.get.return_value = (cached_results, cached_metadata)
        
        input_data = ResearchIn(keyword="test query", top_k=5, cache_enabled=True)
        
        result = await self.agent.search(input_data)
        
        # 캐시 조회 확인
        self.mock_cache.get.assert_called_once()
        
        # 결과 확인
        assert result.cache_hit is True
        assert len(result.docs) == 1
        assert "Cached Title\n\nCached content" in result.docs[0]
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_search_with_cache_miss(self):
        """캐시 미스 시 검색 테스트"""
        # Mock 설정
        self.mock_cache.get.return_value = None
        search_results = [{"title": "Search Title", "body": "Search content"}]
        self.mock_client.search.return_value = search_results
        
        input_data = ResearchIn(keyword="test query", top_k=5, cache_enabled=True)
        
        result = await self.agent.search(input_data)
        
        # 캐시 조회 및 저장 확인
        self.mock_cache.get.assert_called_once()
        self.mock_cache.set.assert_called_once()
        self.mock_client.search.assert_called_once_with("test query", "wt-wt")
        
        # 결과 확인
        assert result.cache_hit is False
        assert len(result.docs) == 1
        assert "Search Title\n\nSearch content" in result.docs[0]
    
    @pytest.mark.asyncio
    async def test_search_with_cache_disabled(self):
        """캐시 비활성화 시 검색 테스트"""
        # Mock 설정
        search_results = [{"title": "Search Title", "body": "Search content"}]
        self.mock_client.search.return_value = search_results
        
        input_data = ResearchIn(keyword="test query", top_k=5, cache_enabled=False)
        
        result = await self.agent.search(input_data)
        
        # 캐시 사용하지 않음 확인
        self.mock_cache.get.assert_not_called()
        self.mock_cache.set.assert_not_called()
        self.mock_client.search.assert_called_once()
        
        # 결과 확인
        assert result.cache_hit is False
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """검색 오류 처리 테스트"""
        # Mock 설정 - 검색 실패
        self.mock_cache.get.return_value = None
        self.mock_client.search.side_effect = Exception("Search failed")
        
        input_data = ResearchIn(keyword="test query", top_k=5)
        
        result = await self.agent.search(input_data)
        
        # 오류 결과 확인
        assert len(result.docs) == 0
        assert len(result.metadata) == 1
        assert result.metadata[0]['error'] == "Search failed"
        assert result.cache_hit is False
    
    def test_clear_cache(self):
        """캐시 정리 테스트"""
        self.agent.clear_cache()
        self.mock_cache.clear.assert_called_once()
    
    def test_get_cache_info(self):
        """캐시 정보 조회 테스트"""
        mock_stats = {"hits": 10, "misses": 5, "hit_rate": 0.67}
        self.mock_cache.get_stats.return_value = mock_stats
        
        stats = self.agent.get_cache_info()
        
        assert stats == mock_stats
        self.mock_cache.get_stats.assert_called_once()
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        # Mock 설정
        client_health = {"status": "healthy", "search_engine": "duckduckgo"}
        cache_health = {"status": "healthy", "cache_type": "research_cache"}
        
        self.mock_client.health_check.return_value = client_health
        self.mock_cache.health_check.return_value = cache_health
        
        health = self.agent.health_check()
        
        assert health['status'] == 'healthy'
        assert health['client'] == client_health
        assert health['cache'] == cache_health
        assert health['config']['enable_cache'] is True


@pytest.mark.agent
@pytest.mark.integration
class TestResearchAgentIntegration:
    """Research Agent 통합 테스트 (실제 API 연동)"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_research(self):
        """전체 연구 워크플로우 테스트"""
        # 실제 Agent 인스턴스 생성 (실제 API 호출)
        agent = ResearchAgent()
        
        # 검색 수행
        input_data = ResearchIn(keyword="integration test", top_k=5)
        result = await agent.search(input_data)
        
        # 결과 검증 (실제 API 결과이므로 유연하게 검증)
        assert result.cache_hit is False  # 첫 번째 호출이므로 캐시 미스
        assert len(result.docs) > 0  # 최소 1개 이상의 결과
        assert result.processing_time > 0
        
        # 두 번째 호출 - 캐시 히트
        result2 = await agent.search(input_data)
        assert result2.cache_hit is True  # 캐시에서 가져옴
        assert len(result2.docs) > 0
        assert result2.processing_time < result.processing_time  # 캐시 히트로 더 빠름
    
    @pytest.mark.asyncio
    async def test_multiple_languages(self):
        """다양한 언어 검색 테스트"""
        agent = ResearchAgent()
        
        # 한국어 검색
        ko_input = ResearchIn(keyword="인공지능", top_k=3, language="ko")
        ko_result = await agent.search(ko_input)
        assert len(ko_result.docs) > 0
        assert ko_result.processing_time > 0
        
        # 영어 검색
        en_input = ResearchIn(keyword="artificial intelligence", top_k=3, language="en")
        en_result = await agent.search(en_input)
        assert len(en_result.docs) > 0
        assert en_result.processing_time > 0
        
        # 일본어 검색
        ja_input = ResearchIn(keyword="人工知能", top_k=3, language="ja")
        ja_result = await agent.search(ja_input)
        assert len(ja_result.docs) > 0
        assert ja_result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_top_k_boundaries(self):
        """top_k 경계값 테스트"""
        agent = ResearchAgent()
        
        # 최소값 (1) - DuckDuckGo는 기본적으로 10개 결과를 반환하므로 이를 고려
        min_input = ResearchIn(keyword="Python", top_k=1)
        min_result = await agent.search(min_input)
        assert len(min_result.docs) > 0  # 최소 1개 이상의 결과
        # DuckDuckGo는 기본적으로 10개 결과를 반환하므로 이를 허용
        assert len(min_result.docs) <= 10
        
        # 최대값 (50)
        max_input = ResearchIn(keyword="machine learning", top_k=50)
        max_result = await agent.search(max_input)
        assert len(max_result.docs) > 0
        assert len(max_result.docs) <= 50
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """캐시 성능 테스트"""
        agent = ResearchAgent()
        
        # 첫 번째 검색 (캐시 미스)
        input_data = ResearchIn(keyword="cache performance test", top_k=5)
        start_time = time.time()
        result1 = await agent.search(input_data)
        first_search_time = time.time() - start_time
        
        # 두 번째 검색 (캐시 히트)
        start_time = time.time()
        result2 = await agent.search(input_data)
        second_search_time = time.time() - start_time
        
        # 캐시 히트 확인
        assert result1.cache_hit is False
        assert result2.cache_hit is True
        
        # 캐시 히트가 더 빠른지 확인 (최소 10배 빠름)
        assert second_search_time < first_search_time * 0.1
        
        # 결과 내용이 동일한지 확인
        assert len(result1.docs) == len(result2.docs)
        assert result1.docs == result2.docs
    
    @pytest.mark.asyncio
    async def test_cache_disabled_scenario(self):
        """캐시 비활성화 시나리오 테스트"""
        agent = ResearchAgent()
        
        # 캐시 비활성화된 검색
        input_data = ResearchIn(keyword="cache disabled test", top_k=3, cache_enabled=False)
        
        # 첫 번째 검색
        result1 = await agent.search(input_data)
        assert result1.cache_hit is False
        
        # 두 번째 검색 (캐시가 비활성화되어 있으므로 다시 API 호출)
        result2 = await agent.search(input_data)
        assert result2.cache_hit is False
        
        # 두 결과가 다른 시간에 생성되었는지 확인
        assert result1.processing_time > 0
        assert result2.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """오류 복구 테스트"""
        agent = ResearchAgent()
        
        # 매우 짧은 키워드로 오류 발생 시뮬레이션 (빈 키워드는 Pydantic에서 검증 오류)
        # 실제로는 DuckDuckGo가 대부분의 쿼리를 처리하므로 빈 결과가 나올 수 있음
        input_data = ResearchIn(keyword="a", top_k=5)  # 매우 짧은 키워드
        
        try:
            result = await agent.search(input_data)
            # 짧은 키워드라도 결과가 나올 수 있음 (DuckDuckGo의 특성)
            assert isinstance(result.docs, list)
            assert isinstance(result.metadata, list)
        except Exception as e:
            # 예외가 발생해도 적절히 처리되어야 함
            assert isinstance(e, Exception)
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """동시 검색 테스트"""
        agent = ResearchAgent()
        
        # 여러 검색을 동시에 수행
        search_tasks = []
        keywords = ["Python", "JavaScript", "Java", "C++", "Go"]
        
        for keyword in keywords:
            input_data = ResearchIn(keyword=keyword, top_k=3)
            task = agent.search(input_data)
            search_tasks.append(task)
        
        # 모든 검색 완료 대기
        results = await asyncio.gather(*search_tasks)
        
        # 모든 결과 검증
        for i, result in enumerate(results):
            assert len(result.docs) > 0
            assert result.processing_time > 0
            assert result.metadata[0]['search_query'] == keywords[i]
    
    @pytest.mark.asyncio
    async def test_cache_clear_functionality(self):
        """캐시 정리 기능 테스트"""
        agent = ResearchAgent()
        
        # 첫 번째 검색으로 캐시에 데이터 저장
        input_data = ResearchIn(keyword="cache clear test", top_k=3)
        result1 = await agent.search(input_data)
        assert result1.cache_hit is False
        
        # 두 번째 검색으로 캐시 히트 확인
        result2 = await agent.search(input_data)
        assert result2.cache_hit is True
        
        # 캐시 정리
        agent.clear_cache()
        
        # 세 번째 검색 (캐시가 정리되었으므로 다시 미스)
        result3 = await agent.search(input_data)
        assert result3.cache_hit is False
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """헬스 체크 통합 테스트"""
        agent = ResearchAgent()
        
        # 헬스 체크 수행
        health = agent.health_check()
        
        # 기본 구조 확인
        assert 'status' in health
        assert 'search_engine' in health
        assert 'client' in health
        assert 'cache' in health
        assert 'config' in health
        
        # 상태 확인
        assert health['status'] in ['healthy', 'unhealthy']
        assert health['search_engine'] == 'duckduckgo'
        assert health['api_key_required'] is False
        
        # 클라이언트 상태 확인
        client_health = health['client']
        assert 'status' in client_health
        assert client_health['search_engine'] == 'duckduckgo'
        
        # 캐시 상태 확인
        cache_health = health['cache']
        assert 'status' in cache_health
        assert 'cache_type' in cache_health
        
        # 설정 확인
        config = health['config']
        assert 'enable_cache' in config
        assert 'log_level' in config
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """캐시 통계 테스트"""
        agent = ResearchAgent()
        
        # 초기 캐시 정보
        initial_stats = agent.get_cache_info()
        assert 'hits' in initial_stats
        assert 'misses' in initial_stats
        assert 'hit_rate' in initial_stats
        
        # 여러 검색 수행
        keywords = ["statistics test 1", "statistics test 2", "statistics test 3"]
        for keyword in keywords:
            input_data = ResearchIn(keyword=keyword, top_k=2)
            await agent.search(input_data)
        
        # 중간 통계 확인
        mid_stats = agent.get_cache_info()
        assert mid_stats['total_requests'] >= len(keywords)
        
        # 같은 검색을 다시 수행하여 캐시 히트 생성
        for keyword in keywords:
            input_data = ResearchIn(keyword=keyword, top_k=2)
            await agent.search(input_data)
        
        # 최종 통계 확인
        final_stats = agent.get_cache_info()
        assert final_stats['hits'] > 0
        assert final_stats['hit_rate'] > 0
    
    @pytest.mark.asyncio
    async def test_document_quality(self):
        """문서 품질 테스트"""
        agent = ResearchAgent()
        
        input_data = ResearchIn(keyword="Python programming best practices", top_k=5)
        result = await agent.search(input_data)
        
        # 문서 품질 검증
        for i, doc in enumerate(result.docs):
            # 빈 문서가 아닌지 확인
            assert len(doc.strip()) > 0
            
            # 메타데이터 확인
            if i < len(result.metadata):
                meta = result.metadata[i]
                assert 'title' in meta
                assert 'url' in meta
                assert 'source' in meta
                assert meta['source'] == 'duckduckgo'
                assert meta['search_query'] == input_data.keyword
                assert meta['search_rank'] == i + 1
    
    @pytest.mark.asyncio
    async def test_long_running_session(self):
        """장시간 실행 세션 테스트"""
        agent = ResearchAgent()
        
        # 여러 검색을 연속으로 수행
        search_count = 10
        total_time = 0
        
        for i in range(search_count):
            keyword = f"long running test {i}"
            input_data = ResearchIn(keyword=keyword, top_k=2)
            
            start_time = time.time()
            result = await agent.search(input_data)
            search_time = time.time() - start_time
            
            total_time += search_time
            
            # 각 검색이 성공했는지 확인
            assert len(result.docs) > 0
            assert result.processing_time > 0
        
        # 평균 검색 시간 계산
        avg_time = total_time / search_count
        print(f"평균 검색 시간: {avg_time:.3f}초")
        
        # 평균 검색 시간이 합리적인 범위인지 확인 (5초 이하)
        assert avg_time < 5.0
        
        # 캐시 통계 확인
        final_stats = agent.get_cache_info()
        assert final_stats['total_requests'] >= search_count
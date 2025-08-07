#!/usr/bin/env python3
"""
Retriever Agent 테스트

RetrieverAgent의 기능을 검증하는 단위 테스트 및 통합 테스트
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 테스트 대상 모듈
from src.agents.retriever import RetrieverAgent, get_retriever_agent
from src.core.schemas.agents import RetrieverIn, RetrieverOut


@pytest.mark.agent
class TestRetrieverAgent:
    """RetrieverAgent 단위 테스트"""
    
    def test_initialization(self):
        """RetrieverAgent 초기화 테스트"""
        agent = RetrieverAgent()
        
        assert agent is not None
        assert hasattr(agent, 'vector_store')
        assert hasattr(agent, '_embeddings_client')
        assert agent._embeddings_client is None
    
    def test_embeddings_client_lazy_loading(self):
        """임베딩 클라이언트 지연 로딩 테스트"""
        agent = RetrieverAgent()
        
        # 처음에는 None
        assert agent._embeddings_client is None
        
        # Mock 임베딩 클라이언트 설정
        mock_embeddings = Mock()
        agent._embeddings_client = mock_embeddings
        
        # 클라이언트 접근 시 캐시된 값 반환
        client = agent.embeddings_client
        assert client == mock_embeddings
    
    def test_create_query_embedding_success(self):
        """쿼리 임베딩 생성 성공 테스트"""
        agent = RetrieverAgent()
        
        # Mock 임베딩 벡터 (4096차원)
        mock_embedding = [0.1] * 4096
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = mock_embedding
        agent._embeddings_client = mock_embeddings
        
        query = "테스트 쿼리"
        result = agent.create_query_embedding(query)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (4096,)
        assert result.dtype == np.float32
        mock_embeddings.embed_query.assert_called_once_with(query)
    
    def test_create_query_embedding_wrong_dimension(self):
        """잘못된 차원의 임베딩 생성 테스트"""
        agent = RetrieverAgent()
        
        # 잘못된 차원의 Mock 임베딩 벡터
        mock_embedding = [0.1] * 100  # 4096이 아닌 100차원
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = mock_embedding
        agent._embeddings_client = mock_embeddings
        
        query = "테스트 쿼리"
        
        with pytest.raises(ValueError, match="임베딩 차원이 올바르지 않습니다"):
            agent.create_query_embedding(query)
    
    def test_create_query_embedding_failure(self):
        """임베딩 생성 실패 테스트"""
        agent = RetrieverAgent()
        
        mock_embeddings = Mock()
        mock_embeddings.embed_query.side_effect = Exception("API 오류")
        agent._embeddings_client = mock_embeddings
        
        query = "테스트 쿼리"
        
        with pytest.raises(ValueError, match="임베딩 생성 실패"):
            agent.create_query_embedding(query)
    
    def test_process_basic(self):
        """기본 처리 테스트"""
        agent = RetrieverAgent()
        
        # Mock 벡터 스토어 검색 결과
        mock_search_results = {
            "ids": [1, 2, 3],
            "distances": np.array([0.1, 0.2, 0.3]),
            "metadata": [
                {"text": "문서 1 내용"},
                {"text": "문서 2 내용"},
                {"text": "문서 3 내용"}
            ]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=3,
                similarity_threshold=0.5,
                include_metadata=True
            )
            
            result = agent.process(input_data)
            
            assert isinstance(result, RetrieverOut)
            assert result.doc_ids == ["1", "2", "3"]
            assert result.similarities == [0.1, 0.2, 0.3]
            assert len(result.metadata) == 3
            assert "[문서 1] 문서 1 내용" in result.context
    
    def test_process_with_content_metadata(self):
        """content 필드가 있는 메타데이터 처리 테스트"""
        agent = RetrieverAgent()
        
        # Mock 벡터 스토어 검색 결과 (content 필드 사용)
        mock_search_results = {
            "ids": [1, 2],
            "distances": np.array([0.1, 0.2]),
            "metadata": [
                {"content": "문서 1 내용"},
                {"content": "문서 2 내용"}
            ]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=2,
                similarity_threshold=0.5,
                include_metadata=True
            )
            
            result = agent.process(input_data)
            
            assert "[문서 1] 문서 1 내용" in result.context
            assert "[문서 2] 문서 2 내용" in result.context
    
    def test_process_with_empty_metadata(self):
        """빈 메타데이터 처리 테스트"""
        agent = RetrieverAgent()
        
        # Mock 벡터 스토어 검색 결과 (빈 메타데이터)
        mock_search_results = {
            "ids": [1],
            "distances": np.array([0.1]),
            "metadata": [{}]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=1,
                similarity_threshold=0.5,
                include_metadata=True
            )
            
            result = agent.process(input_data)
            
            assert "[문서 1] (내용 없음)" in result.context
    
    def test_process_error_handling(self):
        """처리 오류 핸들링 테스트"""
        agent = RetrieverAgent()
        
        with patch.object(agent, 'create_query_embedding') as mock_embed:
            mock_embed.side_effect = ValueError("임베딩 생성 실패")
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=5,
                similarity_threshold=0.5,
                include_metadata=True
            )
            
            with pytest.raises(ValueError, match="검색 처리 실패"):
                agent.process(input_data)
    
    def test_health_check_success(self):
        """상태 점검 성공 테스트"""
        agent = RetrieverAgent()
        
        # Mock 임베딩 클라이언트 설정
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1] * 4096
        agent._embeddings_client = mock_embeddings
        
        # Mock 벡터 스토어 통계
        mock_stats = {
            "index_trained": True,
            "total_vectors": 100,
            "dimension": 4096
        }
        
        with patch.object(agent.vector_store, 'get_index_stats') as mock_stats_func:
            mock_stats_func.return_value = mock_stats
            
            health = agent.health_check()
            
            assert health["status"] == "healthy"
            assert health["embeddings_client"] == "healthy"
            assert health["vector_store"] == mock_stats
            assert "capabilities" in health
    
    def test_health_check_embeddings_failure(self):
        """임베딩 클라이언트 실패 시 상태 점검 테스트"""
        agent = RetrieverAgent()
        
        # Mock 임베딩 클라이언트 설정 (실패)
        mock_embeddings = Mock()
        mock_embeddings.embed_query.side_effect = Exception("임베딩 오류")
        agent._embeddings_client = mock_embeddings
        
        # Mock 벡터 스토어 통계
        mock_stats = {
            "index_trained": True,
            "total_vectors": 100,
            "dimension": 4096
        }
        
        with patch.object(agent.vector_store, 'get_index_stats') as mock_stats_func:
            mock_stats_func.return_value = mock_stats
            
            health = agent.health_check()
            
            assert health["status"] == "degraded"
            assert health["embeddings_client"] == "error"
            assert health["vector_store"] == mock_stats
    
    def test_health_check_vector_store_failure(self):
        """벡터 스토어 실패 시 상태 점검 테스트"""
        agent = RetrieverAgent()
        
        # Mock 임베딩 클라이언트 설정
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1] * 4096
        agent._embeddings_client = mock_embeddings
        
        with patch.object(agent.vector_store, 'get_index_stats') as mock_stats_func:
            mock_stats_func.side_effect = Exception("벡터 스토어 오류")
            
            health = agent.health_check()
            
            assert health["status"] == "error"
            assert "error" in health


@pytest.mark.agent
class TestRetrieverAgentIntegration:
    """RetrieverAgent 통합 테스트"""
    
    def test_end_to_end_retrieval(self):
        """엔드투엔드 검색 테스트"""
        agent = RetrieverAgent()
        
        # Mock 검색 결과
        mock_search_results = {
            "ids": [1, 2, 3],
            "distances": np.array([0.1, 0.2, 0.3]),
            "metadata": [
                {"text": "첫 번째 문서의 내용입니다."},
                {"text": "두 번째 문서의 내용입니다."},
                {"text": "세 번째 문서의 내용입니다."}
            ]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="인공지능과 머신러닝",
                top_k=3,
                similarity_threshold=0.3,
                include_metadata=True
            )
            
            result = agent.process(input_data)
            
            # 결과 검증
            assert len(result.doc_ids) == 3
            assert len(result.similarities) == 3
            assert len(result.metadata) == 3
            assert "첫 번째 문서의 내용입니다" in result.context
            assert "두 번째 문서의 내용입니다" in result.context
            assert "세 번째 문서의 내용입니다" in result.context
    
    def test_high_similarity_threshold(self):
        """높은 유사도 임계값 테스트"""
        agent = RetrieverAgent()
        
        # Mock 검색 결과 (낮은 유사도)
        mock_search_results = {
            "ids": [1, 2],
            "distances": np.array([0.8, 0.9]),  # 높은 거리 = 낮은 유사도
            "metadata": [
                {"text": "문서 1"},
                {"text": "문서 2"}
            ]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=5,
                similarity_threshold=0.9,  # 높은 임계값
                include_metadata=True
            )
            
            result = agent.process(input_data)
            
            # 높은 임계값으로 인해 결과가 필터링될 수 있음
            assert isinstance(result, RetrieverOut)
    
    def test_no_metadata_requested(self):
        """메타데이터 요청하지 않은 경우 테스트"""
        agent = RetrieverAgent()
        
        # Mock 검색 결과
        mock_search_results = {
            "ids": [1, 2],
            "distances": np.array([0.1, 0.2]),
            "metadata": [
                {"text": "문서 1 내용"},
                {"text": "문서 2 내용"}
            ]
        }
        
        with patch.object(agent, 'create_query_embedding') as mock_embed, \
             patch.object(agent.vector_store, 'search') as mock_search:
            
            mock_embed.return_value = np.array([0.1] * 4096)
            mock_search.return_value = mock_search_results
            
            input_data = RetrieverIn(
                query="테스트 쿼리",
                top_k=2,
                similarity_threshold=0.5,
                include_metadata=False  # 메타데이터 요청하지 않음
            )
            
            result = agent.process(input_data)
            
            assert isinstance(result, RetrieverOut)
            assert len(result.doc_ids) == 2
    
    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        agent1 = get_retriever_agent()
        agent2 = get_retriever_agent()
        
        assert agent1 is agent2  # 같은 인스턴스인지 확인
    
    def test_retriever_in_schema_validation(self):
        """RetrieverIn 스키마 검증 테스트"""
        # 유효한 입력
        valid_input = RetrieverIn(
            query="테스트 쿼리",
            top_k=5,
            similarity_threshold=0.5,
            include_metadata=True
        )
        
        assert valid_input.query == "테스트 쿼리"
        assert valid_input.top_k == 5
        assert valid_input.similarity_threshold == 0.5
        assert valid_input.include_metadata is True
        
        # 기본값 검증
        default_input = RetrieverIn(query="기본값 테스트")
        assert default_input.top_k == 5
        assert default_input.similarity_threshold == 0.8  # 실제 기본값
        assert default_input.include_metadata is True
    
    def test_retriever_out_schema_validation(self):
        """RetrieverOut 스키마 검증 테스트"""
        # 유효한 출력
        valid_output = RetrieverOut(
            doc_ids=["1", "2", "3"],
            context="테스트 컨텍스트",
            similarities=[0.1, 0.2, 0.3],
            metadata=[{"text": "문서 1"}, {"text": "문서 2"}, {"text": "문서 3"}]
        )
        
        assert valid_output.doc_ids == ["1", "2", "3"]
        assert valid_output.context == "테스트 컨텍스트"
        assert valid_output.similarities == [0.1, 0.2, 0.3]
        assert len(valid_output.metadata) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
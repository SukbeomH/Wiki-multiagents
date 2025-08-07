"""
Extractor Agent 단위 테스트
"""

import pytest
from unittest.mock import Mock, patch

from src.agents.extractor import ExtractorAgent
from src.core.schemas.agents import ExtractorIn, ExtractorOut


@pytest.mark.agent
class TestExtractorAgent:
    """Extractor Agent 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.agent = ExtractorAgent()
    
    def test_initialization(self):
        """초기화 테스트"""
        assert self.agent is not None
        assert hasattr(self.agent, 'logger')
        assert hasattr(self.agent, 'extract')
        assert hasattr(self.agent, 'health_check')
    
    def test_extract_basic(self):
        """기본 추출 테스트"""
        input_data = ExtractorIn(
            docs=["테스트 문서입니다."],
            extraction_mode="comprehensive"
        )
        
        result = self.agent.extract(input_data)
        
        assert isinstance(result, ExtractorOut)
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)
        assert isinstance(result.processing_stats, dict)
        assert result.processing_stats["processing_time"] >= 0
    
    def test_extract_multiple_docs(self):
        """여러 문서 테스트"""
        input_data = ExtractorIn(
            docs=[
                "첫 번째 테스트 문서입니다.",
                "두 번째 테스트 문서입니다.",
                "세 번째 테스트 문서입니다."
            ],
            extraction_mode="fast"
        )
        
        result = self.agent.extract(input_data)
        
        assert isinstance(result, ExtractorOut)
        assert result.processing_stats["processing_time"] >= 0
    
    def test_extract_different_modes(self):
        """다양한 추출 모드 테스트"""
        extraction_modes = ["comprehensive", "fast", "focused"]
        
        for mode in extraction_modes:
            input_data = ExtractorIn(
                docs=["테스트 문서입니다."],
                extraction_mode=mode
            )
            
            result = self.agent.extract(input_data)
            assert isinstance(result, ExtractorOut)
    
    def test_extract_with_entity_types(self):
        """엔티티 타입 제한 테스트"""
        input_data = ExtractorIn(
            docs=["테스트 문서입니다."],
            extraction_mode="comprehensive",
            entity_types=["PERSON", "ORGANIZATION"]
        )
        
        result = self.agent.extract(input_data)
        assert isinstance(result, ExtractorOut)
    
    def test_extract_with_confidence_threshold(self):
        """신뢰도 임계값 테스트"""
        input_data = ExtractorIn(
            docs=["테스트 문서입니다."],
            extraction_mode="comprehensive",
            min_confidence=0.8
        )
        
        result = self.agent.extract(input_data)
        assert isinstance(result, ExtractorOut)
    
    def test_health_check(self):
        """상태 확인 테스트"""
        health = self.agent.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "agent_type" in health
        assert "timestamp" in health
        assert "health_check_time" in health
        assert health["agent_type"] == "extractor"
        assert health["status"] in ["healthy", "unhealthy"]
    
    def test_health_check_config(self):
        """상태 확인 설정 정보 테스트"""
        health = self.agent.health_check()
        
        if "config" in health:
            config = health["config"]
            assert "extraction_modes" in config
            assert "supported_entity_types" in config
            assert "supported_languages" in config
            assert isinstance(config["extraction_modes"], list)
            assert isinstance(config["supported_entity_types"], list)
            assert isinstance(config["supported_languages"], list)
    
    def test_log_structured(self):
        """구조화된 로깅 테스트"""
        # 로거가 호출되는지 확인
        with patch.object(self.agent.logger, 'info') as mock_info:
            self.agent._log_structured("test_event", test_data="test_value")
            mock_info.assert_called_once()
            
            # JSON 로그가 올바르게 생성되는지 확인
            call_args = mock_info.call_args[0][0]
            assert "test_event" in call_args
            assert "test_value" in call_args
    
    def test_log_structured_with_mock_objects(self):
        """Mock 객체가 포함된 구조화된 로깅 테스트"""
        mock_obj = Mock()
        
        with patch.object(self.agent.logger, 'info') as mock_info:
            self.agent._log_structured("test_event", mock_data=mock_obj)
            mock_info.assert_called_once()
            
            # Mock 객체가 안전하게 처리되는지 확인
            call_args = mock_info.call_args[0][0]
            assert "<Mock>" in call_args
    
    def test_extract_error_handling(self):
        """오류 처리 테스트"""
        # 잘못된 입력으로 오류를 발생시키는 테스트
        # 현재는 플레이스홀더 구현이므로 실제 오류가 발생하지 않음
        # 향후 실제 구현 시 오류 처리 로직 테스트 필요
        
        input_data = ExtractorIn(
            docs=["테스트 문서입니다."],
            extraction_mode="invalid_mode"  # 잘못된 모드
        )
        
        # 오류가 발생해도 유효한 결과를 반환해야 함
        result = self.agent.extract(input_data)
        assert isinstance(result, ExtractorOut)
        assert result.processing_stats["processing_time"] >= 0


@pytest.mark.agent
class TestExtractorAgentIntegration:
    """Extractor Agent 통합 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.agent = ExtractorAgent()
    
    def test_end_to_end_extraction(self):
        """엔드투엔드 추출 테스트"""
        # 실제 문서로 추출 테스트
        test_docs = [
            "삼성전자는 한국의 대표적인 전자제품 회사입니다.",
            "애플과 삼성전자는 스마트폰 시장에서 경쟁 관계입니다.",
            "마이크로소프트는 소프트웨어 회사로 윈도우를 개발했습니다."
        ]
        
        input_data = ExtractorIn(
            docs=test_docs,
            extraction_mode="comprehensive"
        )
        
        result = self.agent.extract(input_data)
        
        assert isinstance(result, ExtractorOut)
        assert result.processing_stats["processing_time"] >= 0
        assert "total_docs" in result.processing_stats
        assert result.processing_stats["total_docs"] == 3
        
        # 현재는 플레이스홀더 구현이므로 실제 추출 결과는 없음
        # 향후 실제 구현 시 결과 검증 로직 추가 필요
    
    def test_large_document_extraction(self):
        """대용량 문서 추출 테스트"""
        # 긴 문서로 성능 테스트
        long_doc = "테스트 문서입니다. " * 1000  # 1000번 반복
        
        input_data = ExtractorIn(
            docs=[long_doc],
            extraction_mode="comprehensive"
        )
        
        result = self.agent.extract(input_data)
        
        assert isinstance(result, ExtractorOut)
        assert result.processing_stats["processing_time"] >= 0
    
    def test_concurrent_extraction(self):
        """동시 추출 테스트"""
        import asyncio
        import concurrent.futures
        
        def extract_single(doc):
            input_data = ExtractorIn(
                docs=[doc],
                extraction_mode="fast"
            )
            return self.agent.extract(input_data)
        
        test_docs = [
            "첫 번째 문서입니다.",
            "두 번째 문서입니다.",
            "세 번째 문서입니다.",
            "네 번째 문서입니다.",
            "다섯 번째 문서입니다."
        ]
        
        # ThreadPoolExecutor를 사용한 동시 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(extract_single, doc) for doc in test_docs]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        assert len(results) == len(test_docs)
        for result in results:
            assert isinstance(result, ExtractorOut)
            assert result.processing_stats["processing_time"] >= 0
    
    def test_processing_stats_validation(self):
        """처리 통계 검증 테스트"""
        input_data = ExtractorIn(
            docs=["테스트 문서입니다."],
            extraction_mode="comprehensive"
        )
        
        result = self.agent.extract(input_data)
        
        # processing_stats 필드 검증
        stats = result.processing_stats
        assert "total_docs" in stats
        assert "extraction_mode" in stats
        assert "entities_found" in stats
        assert "relations_found" in stats
        assert "avg_confidence" in stats
        assert "processing_time" in stats
        
        assert stats["total_docs"] == 1
        assert stats["extraction_mode"] == "comprehensive"
        assert isinstance(stats["entities_found"], int)
        assert isinstance(stats["relations_found"], int)
        assert isinstance(stats["avg_confidence"], float)
        assert isinstance(stats["processing_time"], float)
        assert stats["processing_time"] >= 0 
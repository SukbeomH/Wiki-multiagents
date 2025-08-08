"""
단순화된 ExtractorAgent 테스트

ddgs 라이브러리 충돌을 피하기 위한 독립적인 테스트 파일
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.core.schemas.agents import ExtractorIn, Entity, Relation


class TestExtractorAgentSimplified:
    """단순화된 ExtractorAgent 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        # spaCy 모델 로딩을 모의하여 테스트 속도 향상
        with patch('spacy.load') as mock_spacy_load:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            
            # 엔티티 모의
            mock_ent1 = MagicMock()
            mock_ent1.text = "삼성전자와"
            mock_ent1.label_ = "OG"
            mock_ent1.prob = 0.9
            
            mock_ent2 = MagicMock()
            mock_ent2.text = "애플은"
            mock_ent2.label_ = "OG"
            mock_ent2.prob = 0.8
            
            mock_doc.ents = [mock_ent1, mock_ent2]
            mock_doc.__iter__ = lambda self: iter([])  # 토큰 반복자
            
            mock_nlp.return_value = mock_doc
            mock_spacy_load.return_value = mock_nlp
            
            from src.agents.extractor.agent import ExtractorAgent
            self.agent = ExtractorAgent()
    
    def test_initialization(self):
        """에이전트 초기화 테스트"""
        assert self.agent is not None
        assert hasattr(self.agent, 'extract')
        assert hasattr(self.agent, 'health_check')
    
    def test_extract_basic(self):
        """기본 추출 기능 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자와 애플은 경쟁 관계입니다.'],
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result = self.agent.extract(input_data)
        
        assert result is not None
        assert hasattr(result, 'entities')
        assert hasattr(result, 'relations')
        assert hasattr(result, 'processing_stats')
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)
    
    def test_extract_different_modes(self):
        """다른 extraction_mode 테스트"""
        test_docs = ['삼성전자와 애플은 경쟁 관계입니다.']
        
        # Fast 모드 테스트
        input_data_fast = ExtractorIn(
            docs=test_docs,
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result_fast = self.agent.extract(input_data_fast)
        assert result_fast.processing_stats['extraction_mode'] == 'fast'
        
        # Comprehensive 모드 테스트
        input_data_comp = ExtractorIn(
            docs=test_docs,
            extraction_mode='comprehensive',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result_comp = self.agent.extract(input_data_comp)
        assert result_comp.processing_stats['extraction_mode'] == 'comprehensive'
    
    def test_entity_types_filtering(self):
        """엔티티 타입 필터링 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자와 애플은 경쟁 관계입니다.'],
            extraction_mode='fast',
            entity_types=['PERSON'],  # ORGANIZATION이 아닌 PERSON만 요청
            min_confidence=0.5
        )
        
        result = self.agent.extract(input_data)
        
        # PERSON 타입만 필터링되어야 함
        for entity in result.entities:
            assert entity.type == 'PERSON'
    
    def test_min_confidence_filtering(self):
        """최소 신뢰도 필터링 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자와 애플은 경쟁 관계입니다.'],
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.95  # 높은 신뢰도 요구
        )
        
        result = self.agent.extract(input_data)
        
        # 모든 엔티티가 최소 신뢰도를 만족해야 함
        for entity in result.entities:
            assert entity.confidence >= 0.95
    
    def test_processing_stats(self):
        """처리 통계 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자와 애플은 경쟁 관계입니다.'],
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result = self.agent.extract(input_data)
        stats = result.processing_stats
        
        assert 'total_docs' in stats
        assert 'extraction_mode' in stats
        assert 'entities_found' in stats
        assert 'relations_found' in stats
        assert 'processing_time' in stats
        assert 'method' in stats
        
        assert stats['total_docs'] == 1
        assert stats['extraction_mode'] == 'fast'
        assert stats['entities_found'] >= 0
        assert stats['relations_found'] >= 0
        assert stats['processing_time'] > 0
    
    def test_entity_structure(self):
        """엔티티 구조 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자와 애플은 경쟁 관계입니다.'],
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result = self.agent.extract(input_data)
        
        for entity in result.entities:
            assert hasattr(entity, 'id')
            assert hasattr(entity, 'type')
            assert hasattr(entity, 'name')
            assert hasattr(entity, 'confidence')
            
            assert isinstance(entity.id, str)
            assert isinstance(entity.type, str)
            assert isinstance(entity.name, str)
            assert isinstance(entity.confidence, float)
            assert 0.0 <= entity.confidence <= 1.0
    
    def test_relation_structure(self):
        """관계 구조 테스트"""
        input_data = ExtractorIn(
            docs=['삼성전자가 애플을 인수했습니다.'],
            extraction_mode='fast',
            entity_types=['ORGANIZATION'],
            min_confidence=0.5
        )
        
        result = self.agent.extract(input_data)
        
        for relation in result.relations:
            assert hasattr(relation, 'source')
            assert hasattr(relation, 'target')
            assert hasattr(relation, 'predicate')
            assert hasattr(relation, 'confidence')
            
            assert isinstance(relation.source, str)
            assert isinstance(relation.target, str)
            assert isinstance(relation.predicate, str)
            assert isinstance(relation.confidence, float)
            assert 0.0 <= relation.confidence <= 1.0
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        # spaCy 모델 로딩 실패 상황 테스트
        with patch('spacy.load', side_effect=Exception("Model not found")):
            input_data = ExtractorIn(
                docs=['삼성전자와 애플은 경쟁 관계입니다.'],  # 빈 문서 대신 정상 문서 사용
                extraction_mode='fast',
                entity_types=['ORGANIZATION'],
                min_confidence=0.5
            )
            
            result = self.agent.extract(input_data)
            
            # spaCy 로딩 실패 시 레거시 모드로 전환되어야 함
            assert result is not None
            assert isinstance(result.entities, list)
            assert isinstance(result.relations, list)
            assert result.processing_stats.get('method') == 'legacy'
    
    def test_health_check(self):
        """상태 확인 테스트"""
        health_info = self.agent.health_check()
        
        assert 'status' in health_info
        assert 'agent_type' in health_info
        assert 'timestamp' in health_info
        assert 'config' in health_info
        
        assert health_info['agent_type'] == 'extractor'
        assert 'extraction_modes' in health_info['config']
        assert 'supported_entity_types' in health_info['config']


class TestExtractorAgentKoreanParticles:
    """한국어 조사 처리 테스트"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        with patch('spacy.load'):
            from src.agents.extractor.agent import ExtractorAgent
            self.agent = ExtractorAgent()
    
    def test_remove_korean_particles(self):
        """한국어 조사 제거 테스트"""
        test_cases = [
            ("삼성전자와", "삼성전자"),
            ("애플은", "애플"),
            ("구글에서", "구글"),
            ("마이크로소프트의", "마이크로소프트"),
            ("네이버로", "네이버"),
            ("카카오에게", "카카오"),
            ("삼성전자", "삼성전자"),  # 조사 없는 경우
        ]
        
        for input_text, expected in test_cases:
            result = self.agent._remove_korean_particles(input_text)
            assert result == expected, f"'{input_text}' -> '{result}', expected '{expected}'"


if __name__ == "__main__":
    # 독립 실행을 위한 테스트
    pytest.main([__file__, "-v"]) 
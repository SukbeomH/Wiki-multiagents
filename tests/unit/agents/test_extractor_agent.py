"""
Extractor Agent 단위 테스트

Extractor Agent의 모든 구성 요소에 대한 단위 테스트
- Pydantic 모델 검증
- Azure GPT-4o 클라이언트
- 프롬프트 로더
- 후처리 로직
"""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.schemas.agents import Entity, Relation, ExtractorIn, ExtractorOut
from src.agents.extractor.client import AzureGPT4oClient
from src.agents.extractor.prompt_loader import PromptLoader
from src.agents.extractor.postprocessor import ExtractorPostprocessor
from src.agents.extractor.agent import ExtractorAgent


class TestEntityModel:
    """Entity 모델 테스트"""
    
    def test_valid_entity_creation(self):
        """유효한 엔티티 생성 테스트"""
        entity = Entity(
            id="e1",
            type="PERSON",
            name="김철수",
            start=0,
            end=3,
            confidence=0.9
        )
        
        assert entity.id == "e1"
        assert entity.type == "PERSON"
        assert entity.name == "김철수"
        assert entity.start == 0
        assert entity.end == 3
        assert entity.confidence == 0.9
    
    def test_entity_type_validation(self):
        """엔티티 타입 검증 테스트"""
        # 유효한 타입
        entity = Entity(id="e1", type="PERSON", name="김철수")
        assert entity.type == "PERSON"
        
        # 유효하지 않은 타입 (MISC로 변환)
        with pytest.raises(ValueError):
            Entity(id="e1", type="INVALID_TYPE", name="김철수")
    
    def test_entity_name_validation(self):
        """엔티티 이름 검증 테스트"""
        # 유효한 이름
        entity = Entity(id="e1", type="PERSON", name="김철수")
        assert entity.name == "김철수"
        
        # 빈 이름 (에러 발생)
        with pytest.raises(ValueError):
            Entity(id="e1", type="PERSON", name="")
    
    def test_entity_position_validation(self):
        """엔티티 위치 검증 테스트"""
        # 유효한 위치
        entity = Entity(id="e1", type="PERSON", name="김철수", start=0, end=3)
        assert entity.start == 0
        assert entity.end == 3
        
        # 잘못된 위치 (에러 발생)
        with pytest.raises(ValueError):
            Entity(id="e1", type="PERSON", name="김철수", start=5, end=3)


class TestRelationModel:
    """Relation 모델 테스트"""
    
    def test_valid_relation_creation(self):
        """유효한 관계 생성 테스트"""
        relation = Relation(
            source="e1",
            target="e2",
            predicate="WORKS_FOR",
            confidence=0.8
        )
        
        assert relation.source == "e1"
        assert relation.target == "e2"
        assert relation.predicate == "WORKS_FOR"
        assert relation.confidence == 0.8
    
    def test_relation_type_validation(self):
        """관계 타입 검증 테스트"""
        # 유효한 타입
        relation = Relation(source="e1", target="e2", predicate="WORKS_FOR")
        assert relation.predicate == "WORKS_FOR"
        
        # 유효하지 않은 타입 (RELATED_TO로 변환)
        with pytest.raises(ValueError):
            Relation(source="e1", target="e2", predicate="INVALID_TYPE")
    
    def test_relation_entity_validation(self):
        """관계 엔티티 검증 테스트"""
        # 유효한 엔티티 ID
        relation = Relation(source="e1", target="e2", predicate="WORKS_FOR")
        assert relation.source == "e1"
        assert relation.target == "e2"
        
        # 빈 엔티티 ID (에러 발생)
        with pytest.raises(ValueError):
            Relation(source="", target="e2", predicate="WORKS_FOR")
    
    def test_relation_different_entities(self):
        """출발과 도착 엔티티가 다른지 검증 테스트"""
        # 같은 엔티티 (에러 발생)
        with pytest.raises(ValueError):
            Relation(source="e1", target="e1", predicate="WORKS_FOR")


class TestExtractorInModel:
    """ExtractorIn 모델 테스트"""
    
    def test_valid_extractor_in_creation(self):
        """유효한 ExtractorIn 생성 테스트"""
        extractor_in = ExtractorIn(
            docs=["김철수는 서울대학교에서 컴퓨터공학을 공부했습니다."],
            extraction_mode="comprehensive",
            entity_types=["PERSON", "ORGANIZATION"],
            min_confidence=0.7
        )
        
        assert len(extractor_in.docs) == 1
        assert extractor_in.extraction_mode == "comprehensive"
        assert extractor_in.entity_types == ["PERSON", "ORGANIZATION"]
        assert extractor_in.min_confidence == 0.7
    
    def test_extraction_mode_validation(self):
        """추출 모드 검증 테스트"""
        # 유효한 모드
        extractor_in = ExtractorIn(
            docs=["테스트"],
            extraction_mode="fast"
        )
        assert extractor_in.extraction_mode == "fast"
        
        # 유효하지 않은 모드 (에러 발생)
        with pytest.raises(ValueError):
            ExtractorIn(docs=["테스트"], extraction_mode="invalid_mode")
    
    def test_entity_types_validation(self):
        """엔티티 타입 리스트 검증 테스트"""
        # 유효한 타입 리스트
        extractor_in = ExtractorIn(
            docs=["테스트"],
            entity_types=["PERSON", "ORGANIZATION"]
        )
        assert extractor_in.entity_types == ["PERSON", "ORGANIZATION"]
        
        # 유효하지 않은 타입 (에러 발생)
        with pytest.raises(ValueError):
            ExtractorIn(docs=["테스트"], entity_types=["INVALID_TYPE"])


class TestExtractorOutModel:
    """ExtractorOut 모델 테스트"""
    
    def test_valid_extractor_out_creation(self):
        """유효한 ExtractorOut 생성 테스트"""
        entity = Entity(id="e1", type="PERSON", name="김철수")
        relation = Relation(source="e1", target="e2", predicate="WORKS_FOR")
        
        extractor_out = ExtractorOut(
            entities=[entity],
            relations=[relation],
            processing_stats={"total_docs": 1, "entities_found": 1}
        )
        
        assert len(extractor_out.entities) == 1
        assert len(extractor_out.relations) == 1
        assert extractor_out.processing_stats["total_docs"] == 1


class TestAzureGPT4oClient:
    """Azure GPT-4o 클라이언트 테스트"""
    
    @patch.dict('os.environ', {
        'AOAI_ENDPOINT': 'https://test-endpoint.openai.azure.com/',
        'AOAI_KEY': 'test-key',
        'AOAI_DEPLOYMENT_NAME': 'test-deployment'
    })
    def test_client_initialization(self):
        """클라이언트 초기화 테스트"""
        client = AzureGPT4oClient()
        
        assert client.endpoint == 'https://test-endpoint.openai.azure.com/'
        assert client.api_key == 'test-key'
        assert client.deployment_name == 'test-deployment'
    
    @patch.dict('os.environ', {})
    def test_missing_environment_variables(self):
        """환경 변수 누락 테스트"""
        with pytest.raises(ValueError, match="필수 환경 변수가 설정되지 않았습니다"):
            AzureGPT4oClient()
    
    @patch.dict('os.environ', {
        'AOAI_ENDPOINT': 'invalid-endpoint',
        'AOAI_KEY': 'test-key',
        'AOAI_DEPLOYMENT_NAME': 'test-deployment'
    })
    def test_invalid_endpoint_format(self):
        """잘못된 엔드포인트 형식 테스트"""
        with pytest.raises(ValueError, match="AOAI_ENDPOINT는 https://로 시작해야 합니다"):
            AzureGPT4oClient()
    
    @patch.dict('os.environ', {
        'AOAI_ENDPOINT': 'https://test-endpoint.openai.azure.com/',
        'AOAI_KEY': 'test-key',
        'AOAI_DEPLOYMENT_NAME': 'test-deployment'
    })
    @patch('openai.AzureOpenAI')
    def test_connection_test(self, mock_azure_client):
        """연결 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OK"
        
        mock_azure_client.return_value.chat.completions.create.return_value = mock_response
        
        client = AzureGPT4oClient()
        result = client.test_connection()
        
        assert result["status"] == "success"
        assert result["response"] == "OK"
    
    @patch.dict('os.environ', {
        'AOAI_ENDPOINT': 'https://test-endpoint.openai.azure.com/',
        'AOAI_KEY': 'test-key',
        'AOAI_DEPLOYMENT_NAME': 'test-deployment'
    })
    def test_system_prompt_building(self):
        """시스템 프롬프트 구성 테스트"""
        client = AzureGPT4oClient()
        
        prompt = client._build_system_prompt(
            entity_types=["PERSON", "ORGANIZATION"],
            extraction_mode="comprehensive"
        )
        
        assert "PERSON" in prompt
        assert "ORGANIZATION" in prompt
        assert "comprehensive" in prompt
        assert "JSON 형식" in prompt


class TestPromptLoader:
    """프롬프트 로더 테스트"""
    
    def test_prompt_loader_initialization(self):
        """프롬프트 로더 초기화 테스트"""
        loader = PromptLoader()
        
        assert loader.prompt_data is not None
        assert "system_prompt" in loader.prompt_data
        assert "examples" in loader.prompt_data
    
    def test_system_prompt_generation(self):
        """시스템 프롬프트 생성 테스트"""
        loader = PromptLoader()
        
        prompt = loader.get_system_prompt(
            entity_types=["PERSON", "ORGANIZATION"],
            extraction_mode="comprehensive"
        )
        
        assert "PERSON" in prompt
        assert "ORGANIZATION" in prompt
        assert "comprehensive" in prompt
        assert "JSON 형식" in prompt
    
    def test_example_prompts_loading(self):
        """예시 프롬프트 로드 테스트"""
        loader = PromptLoader()
        
        examples = loader.get_example_prompts()
        
        assert len(examples) >= 1
        assert "name" in examples[0]
        assert "input" in examples[0]
        assert "expected_output" in examples[0]
    
    def test_entity_type_validation(self):
        """엔티티 타입 검증 테스트"""
        loader = PromptLoader()
        
        assert loader.validate_entity_type("PERSON") is True
        assert loader.validate_entity_type("ORGANIZATION") is True
        assert loader.validate_entity_type("INVALID_TYPE") is False
    
    def test_relation_type_validation(self):
        """관계 타입 검증 테스트"""
        loader = PromptLoader()
        
        assert loader.validate_relation_type("WORKS_FOR") is True
        assert loader.validate_relation_type("RELATED_TO") is True
        assert loader.validate_relation_type("INVALID_TYPE") is False
    
    def test_extraction_mode_validation(self):
        """추출 모드 검증 테스트"""
        loader = PromptLoader()
        
        assert loader.validate_extraction_mode("comprehensive") is True
        assert loader.validate_extraction_mode("fast") is True
        assert loader.validate_extraction_mode("focused") is True
        assert loader.validate_extraction_mode("invalid_mode") is False


class TestExtractorPostprocessor:
    """후처리 로직 테스트"""
    
    def test_postprocessor_initialization(self):
        """후처리 로직 초기화 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        assert postprocessor.patterns is not None
        assert "json_block" in postprocessor.patterns
        assert "json_content" in postprocessor.patterns
    
    def test_json_extraction_from_code_block(self):
        """코드 블록에서 JSON 추출 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        response_text = '''
        다음은 추출 결과입니다:
        
        ```json
        {
          "entities": [
            {"id": "e1", "type": "PERSON", "name": "김철수"}
          ],
          "relations": []
        }
        ```
        '''
        
        result = postprocessor.extract_json_from_response(response_text)
        
        assert result is not None
        assert "entities" in result
        assert "relations" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "김철수"
    
    def test_json_extraction_from_content(self):
        """일반 JSON 내용에서 추출 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        response_text = '''
        추출 결과: {"entities": [{"id": "e1", "type": "PERSON", "name": "김철수"}], "relations": []}
        '''
        
        result = postprocessor.extract_json_from_response(response_text)
        
        assert result is not None
        assert "entities" in result
        assert len(result["entities"]) == 1
    
    def test_entity_cleaning_and_validation(self):
        """엔티티 정리 및 검증 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        raw_entities = [
            {
                "id": "e1",
                "type": "PERSON",
                "name": "김철수",
                "start": 0,
                "end": 3,
                "confidence": 0.9
            },
            {
                "id": "e2",
                "type": "ORGANIZATION",
                "name": "서울대학교",
                "start": 6,
                "end": 11,
                "confidence": 0.8
            }
        ]
        
        original_text = "김철수는 서울대학교에서 공부했습니다."
        
        cleaned_entities = postprocessor.clean_and_validate_entities(raw_entities, original_text)
        
        assert len(cleaned_entities) == 2
        assert cleaned_entities[0].name == "김철수"
        assert cleaned_entities[0].type == "PERSON"
        assert cleaned_entities[1].name == "서울대학교"
        assert cleaned_entities[1].type == "ORGANIZATION"
    
    def test_relation_cleaning_and_validation(self):
        """관계 정리 및 검증 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        raw_relations = [
            {
                "source": "e1",
                "target": "e2",
                "predicate": "WORKS_FOR",
                "confidence": 0.8
            }
        ]
        
        entity_ids = ["e1", "e2"]
        
        cleaned_relations = postprocessor.clean_and_validate_relations(raw_relations, entity_ids)
        
        assert len(cleaned_relations) == 1
        assert cleaned_relations[0].source == "e1"
        assert cleaned_relations[0].target == "e2"
        assert cleaned_relations[0].predicate == "WORKS_FOR"
    
    def test_confidence_validation(self):
        """확신도 검증 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        assert postprocessor._validate_confidence(0.5) == 0.5
        assert postprocessor._validate_confidence(1.5) == 1.0
        assert postprocessor._validate_confidence(-0.5) == 0.0
        assert postprocessor._validate_confidence("invalid") == 0.5
    
    def test_entity_type_cleaning(self):
        """엔티티 타입 정리 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        assert postprocessor._clean_entity_type("PERSON") == "PERSON"
        assert postprocessor._clean_entity_type("person") == "PERSON"
        assert postprocessor._clean_entity_type("COMPANY") == "ORGANIZATION"
        assert postprocessor._clean_entity_type("INVALID") == "MISC"
    
    def test_relation_type_cleaning(self):
        """관계 타입 정리 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        assert postprocessor._clean_relation_type("WORKS_FOR") == "WORKS_FOR"
        assert postprocessor._clean_relation_type("works_for") == "WORKS_FOR"
        assert postprocessor._clean_relation_type("RELATED") == "RELATED_TO"
        assert postprocessor._clean_relation_type("INVALID") == "RELATED_TO"
    
    def test_full_postprocessing(self):
        """전체 후처리 테스트"""
        postprocessor = ExtractorPostprocessor()
        
        response_text = '''
        ```json
        {
          "entities": [
            {"id": "e1", "type": "PERSON", "name": "김철수", "start": 0, "end": 3, "confidence": 0.9}
          ],
          "relations": [
            {"source": "e1", "target": "e2", "predicate": "WORKS_FOR", "confidence": 0.8}
          ]
        }
        ```
        '''
        
        original_text = "김철수는 회사에서 일합니다."
        
        result = postprocessor.process_gpt_response(response_text, original_text)
        
        assert result["status"] == "success"
        assert len(result["entities"]) == 1
        assert len(result["relations"]) == 0  # e2가 없으므로 관계는 제거됨


class TestExtractorAgent:
    """Extractor Agent 통합 테스트"""
    
    def test_agent_initialization(self):
        """에이전트 초기화 테스트"""
        agent = ExtractorAgent()
        
        assert agent.logger is not None
        assert hasattr(agent, 'extract')
        assert hasattr(agent, 'health_check')
    
    def test_agent_health_check(self):
        """에이전트 헬스 체크 테스트"""
        agent = ExtractorAgent()
        
        health = agent.health_check()
        
        assert "status" in health
        assert "timestamp" in health
        assert "components" in health


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
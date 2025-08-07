"""
예시 단위 테스트

실제 구현 시 삭제하고 적절한 테스트로 교체하세요.
"""

import pytest


@pytest.mark.unit
def test_basic_functionality():
    """기본 기능 테스트 예시"""
    assert 1 + 1 == 2


@pytest.mark.unit  
def test_with_fixture(sample_document):
    """픽스처 사용 테스트 예시"""
    assert sample_document["id"] == "doc_001"
    assert "content" in sample_document


@pytest.mark.unit
class TestPydanticModels:
    """Pydantic 모델 테스트 예시"""
    
    def test_entity_model_validation(self):
        """엔티티 모델 검증 테스트"""
        # TODO: 실제 Entity 모델 import 후 테스트 작성
        pass
        
    def test_relation_model_validation(self):
        """관계 모델 검증 테스트"""
        # TODO: 실제 Relation 모델 import 후 테스트 작성  
        pass
"""
Fast Strategy

경량 모델을 사용한 빠른 처리 전략
"""

from typing import List, Tuple

from src.core.schemas.agents import ExtractorIn, Entity, Relation
from .extraction_strategy import ExtractionStrategy


class FastStrategy(ExtractionStrategy):
    """빠른 처리를 위한 경량 추출 전략"""
    
    def __init__(self):
        """FastStrategy 초기화"""
        self.entity_extractor = None  # 지연 로딩
        self.relation_extractor = None  # 지연 로딩
        
    def _initialize_extractors(self):
        """추출기들을 지연 초기화합니다."""
        if self.entity_extractor is None:
            from ..extractors import EntityExtractor, RelationExtractor
            
            # 소형 모델 사용 (빠른 처리)
            self.entity_extractor = EntityExtractor(model_name="ko_core_news_sm")
            self.relation_extractor = RelationExtractor(model_name="ko_core_news_sm")
    
    def extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        경량 모델을 통해 빠르게 엔티티와 관계를 추출합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        self._initialize_extractors()
        
        # 배치 처리를 통한 성능 최적화
        if len(input_data.docs) > 1:
            return self._batch_extract(input_data)
        else:
            return self._single_extract(input_data)
    
    def _batch_extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """배치 처리를 통한 빠른 추출을 수행합니다."""
        # 1. 문서 결합 (메모리 효율성)
        combined_text = " ".join(input_data.docs)
        
        # 2. 엔티티 추출 (소형 모델 + 관대한 필터링)
        entities = self.entity_extractor.extract_entities(
            text=combined_text,
            entity_types=input_data.entity_types,
            min_confidence=max(input_data.min_confidence, 0.3)  # 낮은 신뢰도 허용
        )
        
        # 3. 관계 추출 (패턴 기반 우선)
        relations = self.relation_extractor.extract_relations(
            text=combined_text,
            entities=entities,
            min_confidence=max(input_data.min_confidence, 0.4)
        )
        
        # 4. 빠른 후처리
        final_entities = self._fast_postprocess_entities(entities)
        final_relations = self._fast_postprocess_relations(relations)
        
        return final_entities, final_relations
    
    def _single_extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """단일 문서 처리를 수행합니다."""
        doc = input_data.docs[0]
        
        # 1. 엔티티 추출
        entities = self.entity_extractor.extract_entities(
            text=doc,
            entity_types=input_data.entity_types,
            min_confidence=input_data.min_confidence
        )
        
        # 2. 관계 추출
        relations = self.relation_extractor.extract_relations(
            text=doc,
            entities=entities,
            min_confidence=input_data.min_confidence
        )
        
        return entities, relations
    
    def _fast_postprocess_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        엔티티에 대한 빠른 후처리를 수행합니다.
        
        Args:
            entities: 원본 엔티티 리스트
            
        Returns:
            List[Entity]: 후처리된 엔티티 리스트
        """
        # 간단한 중복 제거만 수행
        seen_names = set()
        unique_entities = []
        
        for entity in entities:
            if entity.name not in seen_names:
                seen_names.add(entity.name)
                unique_entities.append(entity)
                
        return unique_entities
    
    def _fast_postprocess_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        관계에 대한 빠른 후처리를 수행합니다.
        
        Args:
            relations: 원본 관계 리스트
            
        Returns:
            List[Relation]: 후처리된 관계 리스트
        """
        # 간단한 중복 제거만 수행
        seen_keys = set()
        unique_relations = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_relations.append(relation)
                
        return unique_relations
    
    def get_strategy_name(self) -> str:
        """전략 이름을 반환합니다."""
        return "fast"
    
    def get_expected_performance(self) -> dict:
        """예상 성능 지표를 반환합니다."""
        return {
            "accuracy": "medium",
            "speed": "fast",
            "memory_usage": "low", 
            "model_size": "small",
            "recommended_for": "development, real-time processing"
        }
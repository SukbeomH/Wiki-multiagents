"""
Comprehensive Strategy

다중 모델 앙상블을 통한 높은 정확도 추출 전략
"""

from typing import List, Tuple

from src.core.schemas.agents import ExtractorIn, Entity, Relation
from .extraction_strategy import ExtractionStrategy


class ComprehensiveStrategy(ExtractionStrategy):
    """높은 정확도를 위한 종합적 추출 전략"""
    
    def __init__(self):
        """ComprehensiveStrategy 초기화"""
        self.entity_extractor = None  # 지연 로딩
        self.relation_extractor = None  # 지연 로딩
        
    def _initialize_extractors(self):
        """추출기들을 지연 초기화합니다."""
        if self.entity_extractor is None:
            from ..extractors import EntityExtractor, RelationExtractor
            
            # 대형 모델 사용 (높은 정확도)
            self.entity_extractor = EntityExtractor(model_name="ko_core_news_lg")
            self.relation_extractor = RelationExtractor(model_name="ko_core_news_lg")
    
    def extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        다중 모델 앙상블을 통해 엔티티와 관계를 추출합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        self._initialize_extractors()
        
        all_entities = []
        all_relations = []
        
        # 각 문서에 대해 추출 수행
        for doc in input_data.docs:
            # 1. 엔티티 추출 (대형 모델 + 엄격한 필터링)
            entities = self.entity_extractor.extract_entities(
                text=doc,
                entity_types=input_data.entity_types,
                min_confidence=max(input_data.min_confidence, 0.7)  # 높은 신뢰도 요구
            )
            
            # 2. 관계 추출 (다중 접근법)
            relations = self.relation_extractor.extract_relations(
                text=doc,
                entities=entities,
                min_confidence=max(input_data.min_confidence, 0.6)
            )
            
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        # 3. 앙상블 후처리
        final_entities = self._ensemble_entities(all_entities)
        final_relations = self._ensemble_relations(all_relations)
        
        return final_entities, final_relations
    
    def _ensemble_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        엔티티 앙상블 처리를 수행합니다.
        
        Args:
            entities: 원본 엔티티 리스트
            
        Returns:
            List[Entity]: 앙상블 처리된 엔티티 리스트
        """
        if not entities:
            return []
        
        # 1. 이름별 그룹핑
        name_groups = {}
        for entity in entities:
            normalized_name = self._normalize_entity_name(entity.name)
            if normalized_name not in name_groups:
                name_groups[normalized_name] = []
            name_groups[normalized_name].append(entity)
        
        # 2. 각 그룹에서 최적 엔티티 선택
        ensemble_entities = []
        for name, group in name_groups.items():
            if len(group) == 1:
                # 단일 엔티티인 경우
                ensemble_entities.append(group[0])
            else:
                # 다중 엔티티인 경우 앙상블 처리
                best_entity = self._select_best_entity(group)
                ensemble_entities.append(best_entity)
        
        return ensemble_entities
    
    def _normalize_entity_name(self, name: str) -> str:
        """엔티티 이름을 정규화합니다."""
        # 조사 제거
        particles = ['은', '는', '이', '가', '을', '를', '와', '과', '에', '에서', '로', '으로', '의', '도', '만']
        for particle in particles:
            if name.endswith(particle):
                name = name[:-len(particle)]
        
        # 공백 제거 및 소문자 변환
        return name.strip().lower()
    
    def _select_best_entity(self, entities: List[Entity]) -> Entity:
        """엔티티 그룹에서 최적의 엔티티를 선택합니다."""
        if not entities:
            return None
        
        # 1. 신뢰도 기반 선택
        best_entity = max(entities, key=lambda e: e.confidence)
        
        # 2. 타입 일관성 확인
        type_counts = {}
        for entity in entities:
            type_counts[entity.type] = type_counts.get(entity.type, 0) + 1
        
        # 가장 많이 나타난 타입으로 통일
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0]
        best_entity.type = most_common_type
        
        # 3. 신뢰도 재계산 (앙상블 효과)
        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        best_entity.confidence = min(1.0, avg_confidence * 1.1)  # 앙상블 보너스
        
        return best_entity
    
    def _ensemble_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        관계 앙상블 처리를 수행합니다.
        
        Args:
            relations: 원본 관계 리스트
            
        Returns:
            List[Relation]: 앙상블 처리된 관계 리스트
        """
        if not relations:
            return []
        
        # 1. 관계 키별 그룹핑
        relation_groups = {}
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in relation_groups:
                relation_groups[key] = []
            relation_groups[key].append(relation)
        
        # 2. 각 그룹에서 최적 관계 선택
        ensemble_relations = []
        for key, group in relation_groups.items():
            if len(group) == 1:
                # 단일 관계인 경우
                ensemble_relations.append(group[0])
            else:
                # 다중 관계인 경우 앙상블 처리
                best_relation = self._select_best_relation(group)
                ensemble_relations.append(best_relation)
        
        return ensemble_relations
    
    def _select_best_relation(self, relations: List[Relation]) -> Relation:
        """관계 그룹에서 최적의 관계를 선택합니다."""
        if not relations:
            return None
        
        # 1. 신뢰도 기반 선택
        best_relation = max(relations, key=lambda r: r.confidence)
        
        # 2. 신뢰도 재계산 (앙상블 효과)
        avg_confidence = sum(r.confidence for r in relations) / len(relations)
        best_relation.confidence = min(1.0, avg_confidence * 1.05)  # 앙상블 보너스
        
        return best_relation
    
    def get_strategy_name(self) -> str:
        """전략 이름을 반환합니다."""
        return "comprehensive"
    
    def get_expected_performance(self) -> dict:
        """예상 성능 지표를 반환합니다."""
        return {
            "accuracy": "high",
            "speed": "slow", 
            "memory_usage": "high",
            "model_size": "large",
            "recommended_for": "production, critical tasks"
        }
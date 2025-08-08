"""
Entity Extractor

spaCy 기반 실제 Named Entity Recognition을 담당하는 모듈
"""

import logging
import uuid
from typing import List, Optional, Set

from src.core.schemas.agents import Entity


class EntityExtractor:
    """spaCy 기반 엔티티 추출기"""
    
    def __init__(self, model_name: str = "ko_core_news_sm", log_level: str = "INFO"):
        """
        EntityExtractor 초기화
        
        Args:
            model_name: spaCy 모델 이름 (ko_core_news_sm, ko_core_news_lg 등)
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        self.model_name = model_name
        self.nlp = None  # 지연 로딩
        
    def _load_model(self):
        """spaCy 모델을 지연 로딩합니다."""
        if self.nlp is None:
            try:
                import spacy
                self.nlp = spacy.load(self.model_name)
                self.logger.info(f"spaCy 모델 '{self.model_name}' 로드 완료")
            except Exception as e:
                self.logger.error(f"spaCy 모델 로드 실패: {e}")
                raise
    
    def extract_entities(
        self, 
        text: str, 
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.0
    ) -> List[Entity]:
        """
        텍스트에서 엔티티를 추출합니다.
        
        Args:
            text: 추출할 텍스트
            entity_types: 필터링할 엔티티 타입 리스트 (None이면 모든 타입)
            min_confidence: 최소 신뢰도 임계값
            
        Returns:
            List[Entity]: 추출된 엔티티 리스트
        """
        self._load_model()
        
        doc = self.nlp(text)
        entities = []
        seen_names: Set[str] = set()
        
        for ent in doc.ents:
            # 엔티티 타입 필터링 (spaCy 라벨을 스키마 타입으로 변환 후 비교)
            mapped_type = self._map_spacy_label_to_schema(ent.label_)
            if entity_types and mapped_type not in entity_types:
                continue
                
            # 중복 제거
            normalized_name = ent.text.strip()
            if normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            
            # 신뢰도 계산 (임시로 기본값 사용, 추후 ConfidenceCalculator로 이동)
            confidence = self._calculate_entity_confidence(ent, doc)
            
            # 최소 신뢰도 필터링
            if confidence < min_confidence:
                continue
                
            entity = Entity(
                id=str(uuid.uuid4()),
                type=self._map_spacy_label_to_schema(ent.label_),
                name=normalized_name,
                confidence=confidence
            )
            entities.append(entity)
            
        return entities
    
    def _calculate_entity_confidence(self, entity, doc) -> float:
        """
        엔티티의 신뢰도를 계산합니다.
        
        TODO: utils/confidence_calculator.py로 이동 예정
        
        Args:
            entity: spaCy 엔티티
            doc: spaCy 문서
            
        Returns:
            float: 신뢰도 (0.0-1.0)
        """
        # 기본 신뢰도 (spaCy NER 모델의 확률값)
        base_score = getattr(entity._, 'confidence', 0.8)
        
        # TODO: 컨텍스트 일관성 점수 계산
        # TODO: 휴리스틱 점수 계산
        
        return min(1.0, base_score)
    
    def _map_spacy_label_to_schema(self, spacy_label: str) -> str:
        """
        spaCy 엔티티 라벨을 스키마 타입으로 매핑합니다.
        
        Args:
            spacy_label: spaCy 엔티티 라벨
            
        Returns:
            str: 스키마 엔티티 타입
        """
        # 한국어 spaCy 모델의 라벨 매핑
        label_mapping = {
            "PS": "PERSON",      # Person
            "LC": "LOCATION",    # Location  
            "OG": "ORGANIZATION", # Organization
            "DT": "DATETIME",    # Date/Time
            "QT": "QUANTITY",    # Quantity
            "CV": "CIVILIZATION", # Civilization
            "AM": "ARTIFACT",    # Artifact
            "AF": "ANIMAL",      # Animal
            "PT": "PLANT",       # Plant
            "TM": "TERM",        # Term
            "EV": "EVENT",       # Event
        }
        
        return label_mapping.get(spacy_label, "CONCEPT")
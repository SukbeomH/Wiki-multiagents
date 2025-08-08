"""
Relation Extractor

의존구문분석 기반 관계 추출을 담당하는 모듈
"""

import logging
import uuid
from typing import List, Dict, Tuple, Optional

from src.core.schemas.agents import Entity, Relation


class RelationExtractor:
    """의존구문분석 기반 관계 추출기"""
    
    def __init__(self, model_name: str = "ko_core_news_sm", log_level: str = "INFO"):
        """
        RelationExtractor 초기화
        
        Args:
            model_name: spaCy 모델 이름
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
                self.logger.info(f"관계 추출용 spaCy 모델 '{self.model_name}' 로드 완료")
            except Exception as e:
                self.logger.error(f"spaCy 모델 로드 실패: {e}")
                raise
    
    def extract_relations(
        self, 
        text: str, 
        entities: List[Entity],
        min_confidence: float = 0.0
    ) -> List[Relation]:
        """
        텍스트와 엔티티 정보를 바탕으로 관계를 추출합니다.
        
        Args:
            text: 추출할 텍스트
            entities: 기추출된 엔티티 리스트
            min_confidence: 최소 신뢰도 임계값
            
        Returns:
            List[Relation]: 추출된 관계 리스트
        """
        self._load_model()
        
        # 의존구문분석 기반 관계 추출
        dependency_relations = self._extract_dependency_relations(text, entities)
        
        # 패턴 기반 관계 추출 (기존 로직 유지)
        pattern_relations = self._extract_pattern_relations(text, entities)
        
        # 관계 병합 및 중복 제거
        all_relations = dependency_relations + pattern_relations
        unique_relations = self._deduplicate_relations(all_relations)
        
        # 신뢰도 필터링
        filtered_relations = [
            rel for rel in unique_relations 
            if rel.confidence >= min_confidence
        ]
        
        return filtered_relations
    
    def _extract_dependency_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """
        의존구문분석을 통해 관계를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            entities: 엔티티 리스트
            
        Returns:
            List[Relation]: 추출된 관계 리스트
        """
        doc = self.nlp(text)
        relations = []
        
        # 엔티티 이름으로 ID 매핑 생성
        name_to_entity = {ent.name: ent for ent in entities}
        entity_names = set(name_to_entity.keys())
        
        # 1. 명사 간 직접 의존관계 분석
        relations.extend(self._extract_noun_dependencies(doc, name_to_entity, entity_names))
        
        # 2. 동사-명사 구조를 통한 관계 분석
        relations.extend(self._extract_verb_noun_relations(doc, name_to_entity, entity_names))
        
        # 3. 복합명사 및 수식 관계 분석
        relations.extend(self._extract_modifier_relations(doc, name_to_entity, entity_names))
        
        # 4. 조사를 활용한 관계 분석 (한국어 특화)
        relations.extend(self._extract_postposition_relations(doc, name_to_entity, entity_names))
        
        return relations
    
    def _extract_noun_dependencies(self, doc, name_to_entity: Dict[str, Entity], entity_names: set) -> List[Relation]:
        """명사 간 직접 의존관계를 분석합니다."""
        relations = []
        
        for token in doc:
            # 엔티티에 해당하는 토큰 찾기
            if any(entity_name in token.text for entity_name in entity_names):
                source_entity = self._find_entity_for_token(token, name_to_entity, entity_names)
                if not source_entity:
                    continue
                    
                # 의존관계 확인
                for child in token.children:
                    if any(entity_name in child.text for entity_name in entity_names):
                        target_entity = self._find_entity_for_token(child, name_to_entity, entity_names)
                        if target_entity and source_entity.id != target_entity.id:
                            
                            # 의존관계 타입에 따른 관계 매핑
                            predicate = self._map_dependency_to_relation(child.dep_)
                            if predicate:
                                confidence = self._calculate_relation_confidence(
                                    source_entity, target_entity, predicate, doc.text
                                )
                                
                                relations.append(Relation(
                                    id=str(uuid.uuid4()),
                                    source=source_entity.id,
                                    target=target_entity.id,
                                    predicate=predicate,
                                    confidence=confidence
                                ))
        
        return relations
    
    def _extract_verb_noun_relations(self, doc, name_to_entity: Dict[str, Entity], entity_names: set) -> List[Relation]:
        """동사-명사 구조를 통한 관계를 분석합니다."""
        relations = []
        
        for token in doc:
            if token.pos_ == "VERB":  # 동사 찾기
                subject_entity = None
                object_entity = None
                
                # 주어와 목적어 찾기
                for child in token.children:
                    if child.dep_ in ["nsubj", "csubj"]:  # 주어
                        subject_entity = self._find_entity_for_token(child, name_to_entity, entity_names)
                    elif child.dep_ in ["obj", "iobj", "dobj"]:  # 목적어
                        object_entity = self._find_entity_for_token(child, name_to_entity, entity_names)
                
                # 주어-목적어 관계 생성
                if subject_entity and object_entity and subject_entity.id != object_entity.id:
                    predicate = self._map_verb_to_relation(token.lemma_)
                    confidence = self._calculate_relation_confidence(
                        subject_entity, object_entity, predicate, doc.text
                    )
                    
                    relations.append(Relation(
                        id=str(uuid.uuid4()),
                        source=subject_entity.id,
                        target=object_entity.id,
                        predicate=predicate,
                        confidence=confidence
                    ))
        
        return relations
    
    def _extract_modifier_relations(self, doc, name_to_entity: Dict[str, Entity], entity_names: set) -> List[Relation]:
        """복합명사 및 수식 관계를 분석합니다."""
        relations = []
        
        for token in doc:
            if any(entity_name in token.text for entity_name in entity_names):
                source_entity = self._find_entity_for_token(token, name_to_entity, entity_names)
                if not source_entity:
                    continue
                
                # 수식어 관계 확인
                for child in token.children:
                    if child.dep_ in ["amod", "nmod", "compound"] and any(entity_name in child.text for entity_name in entity_names):
                        target_entity = self._find_entity_for_token(child, name_to_entity, entity_names)
                        if target_entity and source_entity.id != target_entity.id:
                            
                            predicate = "MODIFIES" if child.dep_ == "amod" else "PART_OF"
                            confidence = self._calculate_relation_confidence(
                                target_entity, source_entity, predicate, doc.text
                            )
                            
                            relations.append(Relation(
                                id=str(uuid.uuid4()),
                                source=target_entity.id,
                                target=source_entity.id,
                                predicate=predicate,
                                confidence=confidence
                            ))
        
        return relations
    
    def _extract_postposition_relations(self, doc, name_to_entity: Dict[str, Entity], entity_names: set) -> List[Relation]:
        """한국어 조사를 활용한 관계를 분석합니다."""
        relations = []
        
        # 한국어 조사-관계 매핑
        postposition_mapping = {
            "의": "BELONGS_TO",
            "와": "COLLABORATES_WITH",
            "과": "COLLABORATES_WITH", 
            "에서": "LOCATED_IN",
            "에게": "INTERACTS_WITH",
            "한테": "INTERACTS_WITH",
            "으로": "USES",
            "로": "USES"
        }
        
        for i, token in enumerate(doc):
            if any(entity_name in token.text for entity_name in entity_names):
                source_entity = self._find_entity_for_token(token, name_to_entity, entity_names)
                if not source_entity:
                    continue
                
                # 다음 토큰이 조사인지 확인
                if i + 1 < len(doc):
                    next_token = doc[i + 1]
                    if next_token.pos_ == "ADP" and next_token.text in postposition_mapping:
                        
                        # 조사 다음에 오는 엔티티 찾기
                        for j in range(i + 2, min(i + 5, len(doc))):  # 근처 토큰 확인
                            candidate_token = doc[j]
                            if any(entity_name in candidate_token.text for entity_name in entity_names):
                                target_entity = self._find_entity_for_token(candidate_token, name_to_entity, entity_names)
                                if target_entity and source_entity.id != target_entity.id:
                                    
                                    predicate = postposition_mapping[next_token.text]
                                    confidence = self._calculate_relation_confidence(
                                        source_entity, target_entity, predicate, doc.text
                                    )
                                    
                                    relations.append(Relation(
                                        id=str(uuid.uuid4()),
                                        source=source_entity.id,
                                        target=target_entity.id,
                                        predicate=predicate,
                                        confidence=confidence
                                    ))
                                break
        
        return relations
    
    def _find_entity_for_token(self, token, name_to_entity: Dict[str, Entity], entity_names: set) -> Optional[Entity]:
        """토큰에 해당하는 엔티티를 찾습니다."""
        # 조사 제거를 위한 한국어 조사 목록
        korean_particles = ['은', '는', '이', '가', '을', '를', '와', '과', '에', '에서', '로', '으로', '의', '도', '만', '부터', '까지', '한테', '에게']
        
        token_text = token.text
        
        # 1. 정확한 매칭 시도
        for entity_name in entity_names:
            if token_text == entity_name:
                return name_to_entity[entity_name]
        
        # 2. 조사 제거 후 매칭 시도
        for particle in korean_particles:
            if token_text.endswith(particle):
                clean_text = token_text[:-len(particle)]
                for entity_name in entity_names:
                    if clean_text == entity_name or entity_name in clean_text:
                        return name_to_entity[entity_name]
        
        # 3. 부분 매칭 시도
        for entity_name in entity_names:
            if entity_name in token_text or token_text in entity_name:
                return name_to_entity[entity_name]
        
        return None
    
    def _map_dependency_to_relation(self, dep_label: str) -> Optional[str]:
        """spaCy 의존관계 라벨을 관계 타입으로 매핑합니다."""
        dep_mapping = {
            "compound": "PART_OF",
            "nmod": "BELONGS_TO", 
            "amod": "MODIFIES",
            "appos": "IS_SAME_AS",
            "conj": "RELATED_TO"
        }
        return dep_mapping.get(dep_label)
    
    def _map_verb_to_relation(self, verb_lemma: str) -> str:
        """동사를 관계 타입으로 매핑합니다."""
        verb_mapping = {
            "인수": "ACQUIRED",
            "투자": "INVESTED_IN", 
            "협력": "COLLABORATES_WITH",
            "경쟁": "COMPETES_WITH",
            "소유": "OWNS",
            "운영": "OPERATES",
            "개발": "DEVELOPS",
            "제조": "MANUFACTURES"
        }
        return verb_mapping.get(verb_lemma, "INTERACTS_WITH")
    
    def _extract_pattern_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """
        규칙 기반 패턴으로 관계를 추출합니다. (기존 로직 유지)
        
        Args:
            text: 분석할 텍스트
            entities: 엔티티 리스트
            
        Returns:
            List[Relation]: 추출된 관계 리스트
        """
        import re
        
        relations = []
        name_to_entity = {ent.name: ent for ent in entities}
        
        # 한국어 관계 패턴 정의 (조사를 포함한 더 유연한 패턴)
        patterns = [
            # 경쟁 관계 - 조사가 붙은 형태도 포함
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?경쟁", "COMPETES_WITH", True),
            (r"(\w+)(?:와|과)\s+(\w+).*?경쟁\s*(?:관계|하)", "COMPETES_WITH", True),
            
            # 협력 관계
            (r"(\w+)(?:와|과)\s+(\w+)(?:은|는)?\s*.*?협력", "COLLABORATES_WITH", True),
            (r"(\w+)(?:와|과)\s+(\w+).*?협력\s*(?:관계|하)", "COLLABORATES_WITH", True),
            (r"(\w+)(?:가|이)\s+(\w+)(?:와|과).*?협력", "COLLABORATES_WITH", True),
            
            # 인수 관계
            (r"(\w+)(?:가|이)\s+(\w+)(?:를|을)\s+인수(?:했|함)", "ACQUIRED", False),
            (r"(\w+)(?:에|의)\s+(\w+)\s+인수", "ACQUIRED", False),
            
            # 투자 관계
            (r"(\w+)(?:가|이)\s+(\w+)(?:에|에게)\s+투자(?:했|함)", "INVESTED_IN", False),
            (r"(\w+)(?:의)\s+(\w+)\s+투자", "INVESTED_IN", False),
            
            # 소속 관계
            (r"(\w+)(?:는|이)\s+(\w+)(?:의)?\s+자회사", "SUBSIDIARY_OF", False),
            (r"(\w+)\s+자회사(?:인)?\s+(\w+)", "SUBSIDIARY_OF", False),
            (r"(\w+)(?:는|이)\s+(\w+)(?:에)\s+속한?", "BELONGS_TO", False),
            
            # 위치 관계
            (r"(\w+)(?:는|이)\s+(\w+)(?:에서|에)\s+(?:위치|있)", "LOCATED_IN", False),
            (r"(\w+)(?:의)\s+(\w+)\s+(?:지점|사무소|본사)", "LOCATED_IN", False),
            
            # 제조/개발 관계
            (r"(\w+)(?:가|이)\s+(\w+)(?:를|을)\s+(?:제조|개발|생산)(?:하|함)", "MANUFACTURES", False),
            (r"(\w+)(?:의)\s+(\w+)\s+(?:제조|개발|생산)", "MANUFACTURES", False),
        ]
        
        for pattern, predicate, bidirectional in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                entity1_name, entity2_name = match.groups()
                
                # 정확한 엔티티 매칭 찾기
                entity1 = self._find_best_entity_match(entity1_name, name_to_entity)
                entity2 = self._find_best_entity_match(entity2_name, name_to_entity)
                
                if entity1 and entity2 and entity1.id != entity2.id:
                    confidence = self._calculate_relation_confidence(entity1, entity2, predicate, text)
                    
                    # 단방향 관계 추가
                    relations.append(Relation(
                        id=str(uuid.uuid4()),
                        source=entity1.id,
                        target=entity2.id,
                        predicate=predicate,
                        confidence=confidence
                    ))
                    
                    # 양방향 관계인 경우 역방향도 추가
                    if bidirectional:
                        relations.append(Relation(
                            id=str(uuid.uuid4()),
                            source=entity2.id,
                            target=entity1.id,
                            predicate=predicate,
                            confidence=confidence
                        ))
        
        return relations
    
    def _find_best_entity_match(self, name: str, name_to_entity: Dict[str, Entity]) -> Optional[Entity]:
        """이름과 가장 잘 매칭되는 엔티티를 찾습니다."""
        # 조사 제거를 위한 한국어 조사 목록
        korean_particles = ['은', '는', '이', '가', '을', '를', '와', '과', '에', '에서', '로', '으로', '의', '도', '만', '부터', '까지', '한테', '에게']
        
        # 1. 정확한 매칭 우선
        if name in name_to_entity:
            return name_to_entity[name]
        
        # 2. 조사 제거 후 매칭 시도
        for particle in korean_particles:
            if name.endswith(particle):
                clean_name = name[:-len(particle)]
                if clean_name in name_to_entity:
                    return name_to_entity[clean_name]
        
        # 3. 부분 매칭
        for entity_name, entity in name_to_entity.items():
            # 원본 이름으로 부분 매칭
            if name in entity_name or entity_name in name:
                return entity
            
            # 조사 제거 후 부분 매칭
            for particle in korean_particles:
                if name.endswith(particle):
                    clean_name = name[:-len(particle)]
                    if clean_name in entity_name or entity_name in clean_name:
                        return entity
        
        return None
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        관계 리스트에서 중복을 제거합니다.
        
        Args:
            relations: 관계 리스트
            
        Returns:
            List[Relation]: 중복 제거된 관계 리스트
        """
        seen = set()
        unique_relations = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
                
        return unique_relations
    
    def _calculate_relation_confidence(
        self, 
        source_entity: Entity, 
        target_entity: Entity, 
        predicate: str,
        context: str
    ) -> float:
        """
        관계의 신뢰도를 계산합니다.
        
        Args:
            source_entity: 시작 엔티티
            target_entity: 목표 엔티티
            predicate: 관계 타입
            context: 컨텍스트 텍스트
            
        Returns:
            float: 신뢰도 (0.0-1.0)
        """
        # 기본 신뢰도
        base_score = 0.7
        
        # 1. 엔티티 타입 호환성 점수
        type_compatibility = self._calculate_type_compatibility(source_entity.type, target_entity.type, predicate)
        
        # 2. 컨텍스트 일관성 점수 (엔티티간 거리)
        context_score = self._calculate_context_consistency(source_entity.name, target_entity.name, context)
        
        # 3. 엔티티 자체 신뢰도
        entity_confidence = (source_entity.confidence + target_entity.confidence) / 2
        
        # 가중 평균으로 최종 신뢰도 계산
        final_confidence = (
            base_score * 0.4 +
            type_compatibility * 0.3 +
            context_score * 0.2 +
            entity_confidence * 0.1
        )
        
        return min(1.0, max(0.1, final_confidence))
    
    def _calculate_type_compatibility(self, source_type: str, target_type: str, predicate: str) -> float:
        """엔티티 타입과 관계 타입의 호환성을 계산합니다."""
        # 관계별 호환 가능한 엔티티 타입 조합
        compatible_types = {
            "COMPETES_WITH": [("ORGANIZATION", "ORGANIZATION"), ("PERSON", "PERSON")],
            "COLLABORATES_WITH": [("ORGANIZATION", "ORGANIZATION"), ("PERSON", "PERSON")],
            "ACQUIRED": [("ORGANIZATION", "ORGANIZATION")],
            "INVESTED_IN": [("ORGANIZATION", "ORGANIZATION"), ("PERSON", "ORGANIZATION")],
            "SUBSIDIARY_OF": [("ORGANIZATION", "ORGANIZATION")],
            "BELONGS_TO": [("ORGANIZATION", "ORGANIZATION"), ("PERSON", "ORGANIZATION")],
            "LOCATED_IN": [("ORGANIZATION", "LOCATION"), ("PERSON", "LOCATION")],
            "MANUFACTURES": [("ORGANIZATION", "CONCEPT"), ("PERSON", "CONCEPT")],
            "OWNS": [("ORGANIZATION", "ORGANIZATION"), ("PERSON", "ORGANIZATION")],
            "OPERATES": [("ORGANIZATION", "CONCEPT"), ("PERSON", "CONCEPT")],
            "DEVELOPS": [("ORGANIZATION", "CONCEPT"), ("PERSON", "CONCEPT")]
        }
        
        if predicate in compatible_types:
            for valid_source, valid_target in compatible_types[predicate]:
                if source_type == valid_source and target_type == valid_target:
                    return 1.0
            return 0.6  # 부분 호환
        
        return 0.8  # 기본값
    
    def _calculate_context_consistency(self, source_name: str, target_name: str, context: str) -> float:
        """컨텍스트 내에서 엔티티 간 거리 기반 일관성을 계산합니다."""
        source_pos = context.find(source_name)
        target_pos = context.find(target_name)
        
        if source_pos == -1 or target_pos == -1:
            return 0.5  # 하나라도 찾을 수 없으면 중간값
        
        distance = abs(source_pos - target_pos)
        
        # 거리가 가까울수록 높은 점수 (최대 100자 이내 최적)
        if distance <= 20:
            return 1.0
        elif distance <= 50:
            return 0.8
        elif distance <= 100:
            return 0.6
        else:
            return 0.4
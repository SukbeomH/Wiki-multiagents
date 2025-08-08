"""
Focused Strategy

특정 엔티티 타입에 특화된 최적화된 추출 전략
"""

from typing import List, Tuple

from src.core.schemas.agents import ExtractorIn, Entity, Relation
from .extraction_strategy import ExtractionStrategy


class FocusedStrategy(ExtractionStrategy):
    """특정 엔티티 타입에 특화된 추출 전략"""
    
    def __init__(self):
        """FocusedStrategy 초기화"""
        self.entity_extractor = None  # 지연 로딩
        self.relation_extractor = None  # 지연 로딩
        
    def _initialize_extractors(self):
        """추출기들을 지연 초기화합니다."""
        if self.entity_extractor is None:
            from ..extractors import EntityExtractor, RelationExtractor
            
            # 중간 크기 모델 사용 (균형)
            self.entity_extractor = EntityExtractor(model_name="ko_core_news_sm")
            self.relation_extractor = RelationExtractor(model_name="ko_core_news_sm")
    
    def extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        특정 엔티티 타입에 특화된 추출을 수행합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        self._initialize_extractors()
        
        # entity_types가 지정된 경우 특화 처리
        if input_data.entity_types:
            return self._focused_extraction(input_data)
        else:
            # 일반 처리 (fast strategy와 유사)
            return self._general_extraction(input_data)
    
    def _focused_extraction(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        특정 엔티티 타입에 특화된 추출을 수행합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        all_entities = []
        all_relations = []
        
        # 타입별 최적화된 추출
        for entity_type in input_data.entity_types:
            optimized_entities = self._extract_type_optimized(
                docs=input_data.docs,
                target_type=entity_type,
                min_confidence=input_data.min_confidence
            )
            all_entities.extend(optimized_entities)
        
        # 특화된 관계 추출 (타입 조합별)
        for doc in input_data.docs:
            relations = self._extract_focused_relations(
                text=doc,
                entities=all_entities,
                target_types=input_data.entity_types,
                min_confidence=input_data.min_confidence
            )
            all_relations.extend(relations)
        
        # 중복 제거 및 최적화
        final_entities = self._optimize_focused_entities(all_entities)
        final_relations = self._optimize_focused_relations(all_relations)
        
        return final_entities, final_relations
    
    def _general_extraction(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        일반적인 추출을 수행합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        all_entities = []
        all_relations = []
        
        for doc in input_data.docs:
            # 일반 엔티티 추출
            entities = self.entity_extractor.extract_entities(
                text=doc,
                entity_types=None,
                min_confidence=input_data.min_confidence
            )
            
            # 일반 관계 추출
            relations = self.relation_extractor.extract_relations(
                text=doc,
                entities=entities,
                min_confidence=input_data.min_confidence
            )
            
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        return all_entities, all_relations
    
    def _extract_type_optimized(
        self, 
        docs: List[str], 
        target_type: str, 
        min_confidence: float
    ) -> List[Entity]:
        """
        특정 타입에 최적화된 엔티티 추출을 수행합니다.
        
        Args:
            docs: 문서 리스트
            target_type: 대상 엔티티 타입
            min_confidence: 최소 신뢰도
            
        Returns:
            List[Entity]: 추출된 엔티티 리스트
        """
        entities = []
        
        # 타입별 특화 키워드 및 패턴
        type_patterns = self._get_type_patterns(target_type)
        
        for doc in docs:
            # 1. 기본 spaCy 추출
            doc_entities = self.entity_extractor.extract_entities(
                text=doc,
                entity_types=[target_type],
                min_confidence=min_confidence
            )
            
            # 2. 타입별 특화 패턴 매칭
            pattern_entities = self._extract_by_patterns(doc, target_type, type_patterns)
            
            # 3. 결과 통합 및 신뢰도 조정
            combined_entities = self._combine_type_entities(doc_entities, pattern_entities, target_type)
            
            entities.extend(combined_entities)
            
        return entities
    
    def _get_type_patterns(self, entity_type: str) -> dict:
        """엔티티 타입별 특화 패턴을 반환합니다."""
        patterns = {
            "PERSON": {
                "keywords": ["회장", "사장", "대표", "CEO", "CTO", "CFO", "이사", "부장", "팀장", "매니저"],
                "name_patterns": [r"([가-힣]{2,4})\s*(?:회장|사장|대표|이사|부장|팀장)"],
                "boost_factor": 1.2
            },
            "ORGANIZATION": {
                "keywords": ["회사", "기업", "그룹", "주식회사", "유한회사", "협회", "재단", "연구소"],
                "name_patterns": [r"([가-힣A-Za-z0-9]+)\s*(?:주식회사|유한회사|회사|기업|그룹)"],
                "boost_factor": 1.1
            },
            "LOCATION": {
                "keywords": ["시", "도", "구", "동", "읍", "면", "국가", "도시", "지역"],
                "name_patterns": [r"([가-힣]+)\s*(?:시|도|구|동|읍|면)"],
                "boost_factor": 1.15
            }
        }
        
        return patterns.get(entity_type, {"keywords": [], "name_patterns": [], "boost_factor": 1.0})
    
    def _extract_by_patterns(self, text: str, entity_type: str, patterns: dict) -> List[Entity]:
        """패턴 기반 엔티티 추출을 수행합니다."""
        import re
        import uuid
        
        entities = []
        
        # 키워드 기반 추출
        for keyword in patterns["keywords"]:
            if keyword in text:
                # 키워드 주변 텍스트에서 엔티티 추출
                keyword_pos = text.find(keyword)
                start_pos = max(0, keyword_pos - 20)
                end_pos = min(len(text), keyword_pos + len(keyword) + 20)
                context = text[start_pos:end_pos]
                
                # 컨텍스트에서 잠재적 엔티티 이름 추출
                potential_names = re.findall(r'([가-힣A-Za-z0-9]{2,10})', context)
                for name in potential_names:
                    if name != keyword and len(name) >= 2:
                        entities.append(Entity(
                            id=str(uuid.uuid4()),
                            type=entity_type,
                            name=name,
                            confidence=0.6 * patterns["boost_factor"]
                        ))
        
        # 정규표현식 패턴 기반 추출
        for pattern in patterns["name_patterns"]:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1)
                entities.append(Entity(
                    id=str(uuid.uuid4()),
                    type=entity_type,
                    name=name,
                    confidence=0.8 * patterns["boost_factor"]
                ))
        
        return entities
    
    def _combine_type_entities(self, spacy_entities: List[Entity], pattern_entities: List[Entity], target_type: str) -> List[Entity]:
        """spaCy 엔티티와 패턴 엔티티를 통합합니다."""
        combined = spacy_entities.copy()
        
        # 패턴 엔티티 중 중복되지 않는 것만 추가
        existing_names = {e.name for e in spacy_entities}
        
        for pattern_entity in pattern_entities:
            if pattern_entity.name not in existing_names:
                combined.append(pattern_entity)
                existing_names.add(pattern_entity.name)
        
        return combined
    
    def _extract_focused_relations(
        self,
        text: str,
        entities: List[Entity], 
        target_types: List[str],
        min_confidence: float
    ) -> List[Relation]:
        """
        타입 조합에 특화된 관계 추출을 수행합니다.
        
        Args:
            text: 분석할 텍스트
            entities: 엔티티 리스트
            target_types: 대상 엔티티 타입 리스트
            min_confidence: 최소 신뢰도
            
        Returns:
            List[Relation]: 추출된 관계 리스트
        """
        # 1. 기본 관계 추출
        base_relations = self.relation_extractor.extract_relations(
            text=text,
            entities=entities,
            min_confidence=min_confidence
        )
        
        # 2. 타입 조합별 특화 관계 추출
        focused_relations = []
        
        # PERSON-ORGANIZATION 관계 특화
        if "PERSON" in target_types and "ORGANIZATION" in target_types:
            person_org_relations = self._extract_person_organization_relations(text, entities)
            focused_relations.extend(person_org_relations)
        
        # ORGANIZATION-ORGANIZATION 관계 특화
        if "ORGANIZATION" in target_types:
            org_org_relations = self._extract_organization_organization_relations(text, entities)
            focused_relations.extend(org_org_relations)
        
        # PERSON-LOCATION 관계 특화
        if "PERSON" in target_types and "LOCATION" in target_types:
            person_loc_relations = self._extract_person_location_relations(text, entities)
            focused_relations.extend(person_loc_relations)
        
        # 3. 결과 통합 및 중복 제거
        all_relations = base_relations + focused_relations
        return self._deduplicate_relations(all_relations)
    
    def _extract_person_organization_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """PERSON-ORGANIZATION 관계를 특화 추출합니다."""
        import re
        import uuid
        
        relations = []
        persons = [e for e in entities if e.type == "PERSON"]
        organizations = [e for e in entities if e.type == "ORGANIZATION"]
        
        # 직책 패턴
        position_patterns = [
            r"(\w+)\s*(?:회장|사장|대표|CEO|CTO|CFO)",
            r"(\w+)\s*(?:이사|부장|팀장|매니저)",
            r"(\w+)\s*(?:소속|근무|재직)"
        ]
        
        for pattern in position_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                person_name = match.group(1)
                person_entity = next((p for p in persons if person_name in p.name or p.name in person_name), None)
                
                if person_entity:
                    # 근처 조직명 찾기
                    for org_entity in organizations:
                        if org_entity.name in text:
                            relations.append(Relation(
                                id=str(uuid.uuid4()),
                                source=person_entity.id,
                                target=org_entity.id,
                                predicate="WORKS_FOR",
                                confidence=0.8
                            ))
        
        return relations
    
    def _extract_organization_organization_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """ORGANIZATION-ORGANIZATION 관계를 특화 추출합니다."""
        import re
        import uuid
        
        relations = []
        organizations = [e for e in entities if e.type == "ORGANIZATION"]
        
        # 경쟁 관계 패턴
        competition_patterns = [
            r"(\w+)\s*와\s*(\w+)\s*경쟁",
            r"(\w+)\s*vs\s*(\w+)",
            r"(\w+)\s*대\s*(\w+)"
        ]
        
        for pattern in competition_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                org1_name, org2_name = match.groups()
                org1 = next((o for o in organizations if org1_name in o.name), None)
                org2 = next((o for o in organizations if org2_name in o.name), None)
                
                if org1 and org2 and org1.id != org2.id:
                    relations.append(Relation(
                        id=str(uuid.uuid4()),
                        source=org1.id,
                        target=org2.id,
                        predicate="COMPETES_WITH",
                        confidence=0.9
                    ))
        
        return relations
    
    def _extract_person_location_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """PERSON-LOCATION 관계를 특화 추출합니다."""
        import re
        import uuid
        
        relations = []
        persons = [e for e in entities if e.type == "PERSON"]
        locations = [e for e in entities if e.type == "LOCATION"]
        
        # 위치 관계 패턴
        location_patterns = [
            r"(\w+)\s*(?:출생|태어난|고향)",
            r"(\w+)\s*(?:거주|살고|주소)",
            r"(\w+)\s*(?:방문|여행)"
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                person_name = match.group(1)
                person_entity = next((p for p in persons if person_name in p.name), None)
                
                if person_entity:
                    # 근처 위치명 찾기
                    for loc_entity in locations:
                        if loc_entity.name in text:
                            relations.append(Relation(
                                id=str(uuid.uuid4()),
                                source=person_entity.id,
                                target=loc_entity.id,
                                predicate="LOCATED_IN",
                                confidence=0.7
                            ))
        
        return relations
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """관계 중복을 제거합니다."""
        seen = set()
        unique_relations = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
        
        return unique_relations
    
    def _optimize_focused_entities(self, entities: List[Entity]) -> List[Entity]:
        """특화된 엔티티 최적화를 수행합니다."""
        # 타입별 중복 제거 및 병합
        type_groups = {}
        for entity in entities:
            if entity.type not in type_groups:
                type_groups[entity.type] = []
            type_groups[entity.type].append(entity)
        
        optimized = []
        for entity_type, group in type_groups.items():
            # 타입별 최적화 로직
            optimized.extend(self._merge_similar_entities(group))
            
        return optimized
    
    def _optimize_focused_relations(self, relations: List[Relation]) -> List[Relation]:
        """특화된 관계 최적화를 수행합니다."""
        # 단순 중복 제거
        seen = set()
        unique_relations = []
        
        for relation in relations:
            key = (relation.source, relation.target, relation.predicate)
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)
                
        return unique_relations
    
    def _merge_similar_entities(self, entities: List[Entity]) -> List[Entity]:
        """유사한 엔티티들을 병합합니다."""
        # TODO: 유사도 기반 엔티티 병합 로직
        # - 이름 유사도 계산
        # - 컨텍스트 유사도 계산
        # - 신뢰도 기반 우선순위
        
        return entities
    
    def get_strategy_name(self) -> str:
        """전략 이름을 반환합니다."""
        return "focused"
    
    def get_expected_performance(self) -> dict:
        """예상 성능 지표를 반환합니다."""
        return {
            "accuracy": "high (for target types)",
            "speed": "medium",
            "memory_usage": "medium",
            "model_size": "small-medium", 
            "recommended_for": "specific domain tasks, targeted extraction"
        }
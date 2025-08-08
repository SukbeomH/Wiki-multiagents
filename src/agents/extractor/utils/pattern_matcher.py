"""
Pattern Matcher

규칙 기반 패턴 매칭을 담당하는 모듈
"""

import logging
import re
import uuid
from typing import List, Dict, Tuple, Optional

from src.core.schemas.agents import Entity, Relation


class PatternMatcher:
    """규칙 기반 패턴 매처"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        PatternMatcher 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 미리 컴파일된 패턴들
        self.entity_patterns = self._compile_entity_patterns()
        self.relation_patterns = self._compile_relation_patterns()
        
    def extract_pattern_entities(self, text: str, entity_types: Optional[List[str]] = None) -> List[Entity]:
        """
        패턴 기반으로 엔티티를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            entity_types: 필터링할 엔티티 타입 (None이면 모든 타입)
            
        Returns:
            List[Entity]: 추출된 엔티티 리스트
        """
        entities = []
        seen_names = set()
        
        for entity_type, patterns in self.entity_patterns.items():
            # 타입 필터링
            if entity_types and entity_type not in entity_types:
                continue
                
            for pattern_name, pattern_regex in patterns.items():
                matches = pattern_regex.finditer(text)
                
                for match in matches:
                    entity_text = match.group(0).strip()
                    
                    # 중복 제거
                    if entity_text in seen_names:
                        continue
                    seen_names.add(entity_text)
                    
                    # 유효성 검증
                    if not self._is_valid_entity_text(entity_text):
                        continue
                    
                    entity = Entity(
                        id=str(uuid.uuid4()),
                        type=entity_type,
                        name=entity_text,
                        confidence=self._calculate_pattern_confidence(pattern_name, entity_text)
                    )
                    entities.append(entity)
                    
        return entities
    
    def extract_pattern_relations(self, text: str, entities: List[Entity]) -> List[Relation]:
        """
        패턴 기반으로 관계를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            entities: 기추출된 엔티티 리스트
            
        Returns:
            List[Relation]: 추출된 관계 리스트
        """
        relations = []
        
        # 엔티티 이름으로 ID 매핑 생성
        name_to_entity = {ent.name: ent for ent in entities}
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern_name, (pattern_regex, direction) in patterns.items():
                matches = pattern_regex.finditer(text)
                
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        entity1_name = groups[0].strip()
                        entity2_name = groups[1].strip()
                        
                        # 엔티티 존재 확인
                        if entity1_name not in name_to_entity or entity2_name not in name_to_entity:
                            continue
                            
                        entity1 = name_to_entity[entity1_name]
                        entity2 = name_to_entity[entity2_name]
                        
                        # 관계 생성
                        new_relations = self._create_relations_from_pattern(
                            entity1, entity2, relation_type, direction, pattern_name
                        )
                        relations.extend(new_relations)
                        
        return self._deduplicate_relations(relations)
    
    def _compile_entity_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """엔티티 추출 패턴들을 컴파일합니다."""
        patterns = {
            "PERSON": {
                "korean_name": re.compile(r'[가-힣]{2,4}(?:\s+[가-힣]{2,4})?'),
                "english_name": re.compile(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+'),
                "title_name": re.compile(r'(?:대표|회장|사장|부장|과장|팀장|이사|상무|전무|CEO|CTO|CFO)\s+[가-힣]{2,4}'),
                "korean_full_name": re.compile(r'[가-힣]{2,4}\s+[가-힣]{2,4}'),  # 성+이름
                "nickname": re.compile(r'[가-힣]{2,4}(?:님|씨|군|양)'),
            },
            "ORGANIZATION": {
                "company_suffix": re.compile(r'[가-힣A-Za-z0-9]+(?:주식회사|회사|기업|그룹|재단|은행|대학|연구소|공사)'),
                "english_company": re.compile(r'[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*(?:\s+(?:Inc|Corp|Corporation|Ltd|LLC|Co\.))'),
                "organization_keyword": re.compile(r'(?:부|청|처|국|원|센터|기관)\s*[가-힣]+'),
                "startup": re.compile(r'[가-힣A-Za-z0-9]+(?:스타트업|벤처|테크)'),
                "department": re.compile(r'[가-힣A-Za-z]+(?:부서|팀|실|과|계)'),
            },
            "LOCATION": {
                "korean_location": re.compile(r'[가-힣]+(?:시|군|구|읍|면|동|리|로|길)'),
                "country": re.compile(r'(?:대한민국|한국|미국|중국|일본|영국|프랑스|독일|이탈리아|스페인|러시아|인도)'),
                "city": re.compile(r'(?:서울|부산|대구|인천|광주|대전|울산|수원|성남|고양|용인|청주|천안|전주|포항|창원)'),
                "district": re.compile(r'[가-힣]+(?:구|동|읍|면)'),
                "building": re.compile(r'[가-힣A-Za-z0-9]+(?:빌딩|타워|센터|플라자|몰)'),
            },
            "DATETIME": {
                "year": re.compile(r'\d{4}년'),
                "month_day": re.compile(r'\d{1,2}월\s*\d{1,2}일'),
                "full_date": re.compile(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일'),
                "time": re.compile(r'\d{1,2}시\s*\d{1,2}분'),
                "period": re.compile(r'\d{4}년\s*부터\s*\d{4}년\s*까지'),
            },
            "QUANTITY": {
                "money": re.compile(r'\d+(?:,\d{3})*\s*(?:원|달러|엔|유로|위안)'),
                "percentage": re.compile(r'\d+(?:\.\d+)?%'),
                "count": re.compile(r'\d+(?:,\d{3})*\s*(?:개|명|건|회|번|차례)'),
                "size": re.compile(r'\d+(?:\.\d+)?\s*(?:MB|GB|TB|KB|픽셀|px)'),
                "ratio": re.compile(r'\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?'),
            },
            "TECHNOLOGY": {
                "tech_term": re.compile(r'(?:AI|ML|DL|NLP|API|SDK|UI|UX|VR|AR|IoT|5G|블록체인|클라우드)'),
                "programming": re.compile(r'(?:Python|Java|JavaScript|C\+\+|React|Vue|Angular|Node\.js|Django|Flask)'),
                "platform": re.compile(r'(?:AWS|Azure|GCP|네이버|카카오|구글|애플|페이스북|트위터)'),
            }
        }
        
        return patterns
    
    def _compile_relation_patterns(self) -> Dict[str, Dict[str, Tuple[re.Pattern, str]]]:
        """관계 추출 패턴들을 컴파일합니다."""
        # 간단한 이름 패턴 (한글/영문/숫자 2자 이상)
        name = r'([A-Za-z가-힣0-9]{2,})'
        
        patterns = {
            "COMPETES_WITH": {
                "competition_1": (re.compile(fr'{name}와 {name}는 경쟁 관계'), "bidir"),
                "competition_2": (re.compile(fr'{name}와 {name}은 경쟁 관계'), "bidir"),
                "competition_3": (re.compile(fr'{name}와 {name}의 경쟁'), "bidir"),
                "rival": (re.compile(fr'{name}의 라이벌인 {name}'), "bidir"),
                "vs": (re.compile(fr'{name}\s*vs\s*{name}'), "bidir"),
                "against": (re.compile(fr'{name} 대 {name}'), "bidir"),
            },
            "COLLABORATES_WITH": {
                "collaboration_1": (re.compile(fr'{name}와 {name}는 협력 관계'), "bidir"),
                "collaboration_2": (re.compile(fr'{name}와 {name}은 협력 관계'), "bidir"),
                "collaboration_3": (re.compile(fr'{name}가 {name}와 협력'), "bidir"),
                "partnership": (re.compile(fr'{name}와 {name}의 파트너십'), "bidir"),
                "joint": (re.compile(fr'{name}와 {name}의 공동'), "bidir"),
                "alliance": (re.compile(fr'{name}와 {name}의 제휴'), "bidir"),
            },
            "ACQUIRED": {
                "acquisition_1": (re.compile(fr'{name}가 {name}를 인수(하였다|했다)'), "fwd"),
                "acquisition_2": (re.compile(fr'{name}가 {name}을 인수(하였다|했다)'), "fwd"),
                "acquisition_3": (re.compile(fr'{name}의 {name} 인수'), "fwd"),
                "bought": (re.compile(fr'{name}가 {name}를 매입(하였다|했다)'), "fwd"),
                "merger": (re.compile(fr'{name}와 {name}의 합병'), "bidir"),
                "takeover": (re.compile(fr'{name}의 {name} 인수합병'), "fwd"),
            },
            "SUBSIDIARY_OF": {
                "subsidiary_1": (re.compile(fr'{name}는 {name}의 자회사'), "fwd"),
                "subsidiary_2": (re.compile(fr'{name}의 자회사인 {name}'), "rev"),
                "subsidiary_3": (re.compile(fr'{name}의 계열사인 {name}'), "rev"),
                "affiliate": (re.compile(fr'{name}의 지사인 {name}'), "rev"),
                "branch": (re.compile(fr'{name}의 분사인 {name}'), "rev"),
            },
            "WORKS_FOR": {
                "employment_1": (re.compile(fr'{name}는 {name}에서 근무'), "fwd"),
                "employment_2": (re.compile(fr'{name} 소속 {name}'), "rev"),
                "employment_3": (re.compile(fr'{name} 직원 {name}'), "rev"),
                "position": (re.compile(fr'{name}의 {name}'), "rev"),
                "team": (re.compile(fr'{name} 팀의 {name}'), "rev"),
            },
            "LOCATED_IN": {
                "location_1": (re.compile(fr'{name}는 {name}에 위치'), "fwd"),
                "location_2": (re.compile(fr'{name}에 있는 {name}'), "rev"),
                "location_3": (re.compile(fr'{name} 소재의 {name}'), "rev"),
                "based_in": (re.compile(fr'{name} 기반의 {name}'), "rev"),
                "headquarters": (re.compile(fr'{name}의 본사가 {name}'), "fwd"),
            },
            "MANUFACTURES": {
                "manufacture_1": (re.compile(fr'{name}가 {name}를 제조'), "fwd"),
                "manufacture_2": (re.compile(fr'{name}의 {name} 생산'), "fwd"),
                "develop": (re.compile(fr'{name}가 {name}를 개발'), "fwd"),
                "create": (re.compile(fr'{name}의 {name} 제작'), "fwd"),
            },
            "INVESTED_IN": {
                "investment_1": (re.compile(fr'{name}가 {name}에 투자'), "fwd"),
                "investment_2": (re.compile(fr'{name}의 {name} 투자'), "fwd"),
                "funding": (re.compile(fr'{name}가 {name}를 지원'), "fwd"),
                "sponsor": (re.compile(fr'{name}의 {name} 후원'), "fwd"),
            },
            "BELONGS_TO": {
                "belong_1": (re.compile(fr'{name}는 {name}에 속함'), "fwd"),
                "belong_2": (re.compile(fr'{name}의 {name}'), "rev"),
                "part_of": (re.compile(fr'{name}의 일부인 {name}'), "rev"),
            }
        }
        
        return patterns
    
    def _create_relations_from_pattern(
        self,
        entity1: Entity,
        entity2: Entity, 
        relation_type: str,
        direction: str,
        pattern_name: str
    ) -> List[Relation]:
        """패턴 매칭 결과로부터 관계를 생성합니다."""
        relations = []
        confidence = self._calculate_pattern_confidence(pattern_name, "")
        
        if direction == "fwd":
            # entity1 -> entity2
            relations.append(Relation(
                source=entity1.id,
                target=entity2.id,
                predicate=relation_type,
                confidence=confidence
            ))
        elif direction == "rev":
            # entity2 -> entity1  
            relations.append(Relation(
                source=entity2.id,
                target=entity1.id,
                predicate=relation_type,
                confidence=confidence
            ))
        elif direction == "bidir":
            # 양방향
            relations.append(Relation(
                source=entity1.id,
                target=entity2.id,
                predicate=relation_type,
                confidence=confidence
            ))
            relations.append(Relation(
                source=entity2.id,
                target=entity1.id, 
                predicate=relation_type,
                confidence=confidence
            ))
            
        return relations
    
    def _calculate_pattern_confidence(self, pattern_name: str, text: str) -> float:
        """패턴별 신뢰도를 계산합니다."""
        # 패턴별 기본 신뢰도
        pattern_confidences = {
            # 엔티티 패턴
            "korean_name": 0.7,
            "english_name": 0.8,
            "title_name": 0.9,
            "company_suffix": 0.9,
            "english_company": 0.8,
            "organization_keyword": 0.7,
            "korean_location": 0.8,
            "country": 0.9,
            "city": 0.9,
            "year": 0.9,
            "month_day": 0.8,
            "full_date": 0.9,
            "money": 0.9,
            "percentage": 0.9,
            "count": 0.8,
            
            # 관계 패턴  
            "competition_1": 0.9,
            "competition_2": 0.9,
            "rival": 0.8,
            "collaboration_1": 0.9,
            "collaboration_2": 0.9,
            "partnership": 0.8,
            "acquisition_1": 0.9,
            "acquisition_2": 0.9,
            "bought": 0.8,
            "subsidiary_1": 0.9,
            "subsidiary_2": 0.9,
            "affiliate": 0.8,
            "employment_1": 0.8,
            "employment_2": 0.8,
            "employee": 0.7,
            "location_1": 0.8,
            "location_2": 0.8,
            "based_in": 0.7,
        }
        
        base_confidence = pattern_confidences.get(pattern_name, 0.5)
        
        # 텍스트 길이 기반 조정
        if text:
            if len(text) >= 3:
                base_confidence += 0.1
            if len(text) >= 5:
                base_confidence += 0.1
                
        return min(1.0, base_confidence)
    
    def _is_valid_entity_text(self, text: str) -> bool:
        """유효한 엔티티 텍스트인지 검증합니다."""
        if not text or len(text.strip()) < 2:
            return False
            
        # 너무 긴 텍스트 제외
        if len(text) > 50:
            return False
            
        # 숫자로만 구성된 경우 제외 (날짜/수량 패턴 제외)
        if text.isdigit() and len(text) > 4:
            return False
            
        return True
    
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
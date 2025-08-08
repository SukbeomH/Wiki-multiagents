"""
Confidence Calculator

엔티티 및 관계의 신뢰도를 계산하는 모듈
"""

import logging
from typing import List, Optional

from src.core.schemas.agents import Entity, Relation


class ConfidenceCalculator:
    """신뢰도 계산기"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        ConfidenceCalculator 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
    def calculate_entity_confidence(
        self, 
        entity,  # spaCy entity 객체
        doc,     # spaCy doc 객체
        context: Optional[str] = None
    ) -> float:
        """
        엔티티의 신뢰도를 계산합니다.
        
        Args:
            entity: spaCy 엔티티
            doc: spaCy 문서
            context: 추가 컨텍스트
            
        Returns:
            float: 신뢰도 (0.0-1.0)
        """
        # 1. NER 모델 기본 확률값
        base_score = self._get_ner_model_confidence(entity)
        
        # 2. 컨텍스트 일관성 점수
        context_score = self._calculate_context_consistency(entity, doc)
        
        # 3. 휴리스틱 점수
        heuristic_score = self._calculate_entity_heuristic_score(entity, doc)
        
        # 가중 평균 계산
        final_score = (
            base_score * 0.5 +
            context_score * 0.3 + 
            heuristic_score * 0.2
        )
        
        return min(1.0, max(0.0, final_score))
    
    def calculate_relation_confidence(
        self,
        source_entity: Entity,
        target_entity: Entity, 
        predicate: str,
        context: str,
        extraction_method: str = "pattern"
    ) -> float:
        """
        관계의 신뢰도를 계산합니다.
        
        Args:
            source_entity: 시작 엔티티
            target_entity: 목표 엔티티
            predicate: 관계 타입
            context: 컨텍스트 텍스트
            extraction_method: 추출 방법 (pattern, dependency, llm)
            
        Returns:
            float: 신뢰도 (0.0-1.0)
        """
        # 1. 추출 방법별 기본 점수
        base_score = self._get_extraction_method_confidence(extraction_method)
        
        # 2. 엔티티 타입 호환성 점수
        compatibility_score = self._calculate_type_compatibility(
            source_entity.type, target_entity.type, predicate
        )
        
        # 3. 컨텍스트 지원 점수
        context_support_score = self._calculate_context_support(
            source_entity.name, target_entity.name, predicate, context
        )
        
        # 4. 엔티티 신뢰도 영향
        entity_confidence_factor = min(source_entity.confidence, target_entity.confidence)
        
        # 가중 평균 계산
        final_score = (
            base_score * 0.3 +
            compatibility_score * 0.3 +
            context_support_score * 0.3 +
            entity_confidence_factor * 0.1
        )
        
        return min(1.0, max(0.0, final_score))
    
    def _get_ner_model_confidence(self, entity) -> float:
        """NER 모델의 확률값을 가져옵니다."""
        # spaCy 엔티티의 confidence 속성 확인
        if hasattr(entity._, 'confidence'):
            return float(entity._.confidence)
        
        # spaCy 기본 NER의 경우 확률값이 직접 제공되지 않으므로
        # 엔티티 길이와 타입을 기반으로 휴리스틱 점수 계산
        length_score = min(1.0, len(entity.text) / 10.0)  # 길이가 길수록 신뢰도 증가
        type_score = self._get_type_base_confidence(entity.label_)
        
        return (length_score + type_score) / 2.0
    
    def _calculate_context_consistency(self, entity, doc) -> float:
        """컨텍스트 일관성을 계산합니다."""
        score = 0.5  # 기본 점수
        
        # 1. 주변 토큰과의 의미적 일관성
        context_score = self._analyze_context_tokens(entity, doc)
        score += context_score * 0.3
        
        # 2. 문서 내 다른 엔티티와의 관계
        entity_relation_score = self._analyze_entity_relations(entity, doc)
        score += entity_relation_score * 0.2
        
        # 3. 도메인 특화 키워드 공존
        domain_score = self._analyze_domain_keywords(entity, doc)
        score += domain_score * 0.2
        
        return min(1.0, score)
    
    def _analyze_context_tokens(self, entity, doc) -> float:
        """주변 토큰과의 의미적 일관성을 분석합니다."""
        score = 0.0
        
        # 엔티티 주변 토큰들 분석
        entity_start = entity.start
        entity_end = entity.end
        
        # 앞뒤 3개 토큰 확인
        context_tokens = []
        for i in range(max(0, entity_start - 3), min(len(doc), entity_end + 3)):
            if i < entity_start or i >= entity_end:
                context_tokens.append(doc[i])
        
        # 대문자로 시작하는 토큰이 많을수록 고유명사 가능성 높음
        capital_count = sum(1 for token in context_tokens if token.text[0].isupper())
        if capital_count > 0:
            score += min(0.3, capital_count * 0.1)
        
        # 특정 품사와의 조합 점수
        for token in context_tokens:
            if token.pos_ in ["PROPN", "NOUN"]:  # 고유명사, 일반명사
                score += 0.1
            elif token.pos_ in ["VERB", "AUX"]:  # 동사, 조동사
                score += 0.05
                
        return min(1.0, score)
    
    def _analyze_entity_relations(self, entity, doc) -> float:
        """문서 내 다른 엔티티와의 관계를 분석합니다."""
        score = 0.0
        
        # 같은 타입의 다른 엔티티들과의 거리 분석
        same_type_entities = [ent for ent in doc.ents if ent.label_ == entity.label_ and ent != entity]
        
        if same_type_entities:
            # 같은 타입 엔티티가 많을수록 해당 타입의 신뢰도 증가
            score += min(0.2, len(same_type_entities) * 0.05)
            
            # 엔티티 간 거리 분석 (가까울수록 관련성 높음)
            for other_entity in same_type_entities:
                distance = abs(entity.start - other_entity.start)
                if distance <= 10:  # 10토큰 이내
                    score += 0.1
                    
        return min(1.0, score)
    
    def _analyze_domain_keywords(self, entity, doc) -> float:
        """도메인 특화 키워드와의 공존을 분석합니다."""
        score = 0.0
        
        # 엔티티 타입별 도메인 키워드
        domain_keywords = {
            "PS": ["회장", "사장", "대표", "이사", "부장", "팀장", "CEO", "CTO", "CFO"],
            "OG": ["회사", "기업", "그룹", "주식회사", "유한회사", "협회", "재단"],
            "LC": ["시", "도", "구", "동", "읍", "면", "국가", "도시", "지역"],
            "DT": ["년", "월", "일", "시", "분", "초", "주", "개월"],
            "QT": ["원", "달러", "엔", "유로", "위안", "%", "개", "명", "건"]
        }
        
        keywords = domain_keywords.get(entity.label_, [])
        doc_text = doc.text.lower()
        
        # 키워드 공존 점수
        for keyword in keywords:
            if keyword in doc_text:
                score += 0.1
                
        return min(1.0, score)
    
    def _calculate_entity_heuristic_score(self, entity, doc) -> float:
        """엔티티 휴리스틱 점수를 계산합니다."""
        score = 0.5  # 기본 점수
        
        # 대문자로 시작하는 경우 (고유명사 가능성)
        if entity.text[0].isupper():
            score += 0.2
            
        # 특정 패턴 매칭 (이메일, URL 등)
        if self._matches_known_patterns(entity.text):
            score += 0.2
            
        # 길이 기반 조정
        if len(entity.text) >= 3:
            score += 0.1
            
        return min(1.0, score)
    
    def _get_extraction_method_confidence(self, method: str) -> float:
        """추출 방법별 기본 신뢰도를 반환합니다."""
        method_scores = {
            "pattern": 0.8,      # 패턴 매칭은 정확하지만 범위 제한적
            "dependency": 0.7,   # 의존구문분석은 언어학적 근거 있음
            "llm": 0.6,         # LLM은 유연하지만 불확실성 존재
            "hybrid": 0.8       # 하이브리드 접근법
        }
        return method_scores.get(method, 0.5)
    
    def _calculate_type_compatibility(self, source_type: str, target_type: str, predicate: str) -> float:
        """엔티티 타입과 관계의 호환성을 계산합니다."""
        # 타입 조합별 관계 호환성 매트릭스
        compatibility_matrix = {
            ("PERSON", "ORGANIZATION", "WORKS_FOR"): 0.9,
            ("PERSON", "PERSON", "KNOWS"): 0.8,
            ("ORGANIZATION", "ORGANIZATION", "COMPETES_WITH"): 0.9,
            ("ORGANIZATION", "ORGANIZATION", "ACQUIRED"): 0.8,
            ("PERSON", "LOCATION", "BORN_IN"): 0.9,
            ("PERSON", "LOCATION", "LIVES_IN"): 0.8,
        }
        
        key = (source_type, target_type, predicate)
        return compatibility_matrix.get(key, 0.5)  # 기본값
    
    def _calculate_context_support(
        self, 
        source_name: str, 
        target_name: str, 
        predicate: str, 
        context: str
    ) -> float:
        """컨텍스트에서 관계를 지원하는 증거를 찾습니다."""
        score = 0.5  # 기본 점수
        
        # 1. 관계 키워드 공존 분석
        keyword_score = self._analyze_relation_keywords(predicate, context)
        score += keyword_score * 0.3
        
        # 2. 엔티티 간 거리 분석
        distance_score = self._analyze_entity_distance(source_name, target_name, context)
        score += distance_score * 0.3
        
        # 3. 문장 구조 분석
        structure_score = self._analyze_sentence_structure(source_name, target_name, predicate, context)
        score += structure_score * 0.2
        
        return min(1.0, score)
    
    def _analyze_relation_keywords(self, predicate: str, context: str) -> float:
        """관계 타입별 키워드 공존을 분석합니다."""
        score = 0.0
        
        # 관계 타입별 키워드 매핑
        relation_keywords = {
            "COMPETES_WITH": ["경쟁", "라이벌", "대항", "vs", "대", "상대"],
            "COLLABORATES_WITH": ["협력", "파트너십", "제휴", "공동", "함께"],
            "ACQUIRED": ["인수", "매입", "합병", "인수합병", "M&A"],
            "SUBSIDIARY_OF": ["자회사", "계열사", "지사", "분사"],
            "WORKS_FOR": ["근무", "소속", "재직", "직원", "사원"],
            "LOCATED_IN": ["위치", "소재", "기반", "본사", "지점"],
            "BELONGS_TO": ["소속", "관할", "하위", "부서"],
            "MANUFACTURES": ["제조", "생산", "개발", "만들다"],
            "INVESTED_IN": ["투자", "자본", "지원", "후원"]
        }
        
        keywords = relation_keywords.get(predicate, [])
        context_lower = context.lower()
        
        # 키워드 공존 점수
        for keyword in keywords:
            if keyword in context_lower:
                score += 0.2
                
        return min(1.0, score)
    
    def _analyze_entity_distance(self, source_name: str, target_name: str, context: str) -> float:
        """엔티티 간 거리를 분석합니다."""
        source_pos = context.find(source_name)
        target_pos = context.find(target_name)
        
        if source_pos == -1 or target_pos == -1:
            return 0.3  # 하나라도 찾을 수 없으면 낮은 점수
        
        distance = abs(source_pos - target_pos)
        
        # 거리가 가까울수록 높은 점수
        if distance <= 20:
            return 1.0
        elif distance <= 50:
            return 0.8
        elif distance <= 100:
            return 0.6
        else:
            return 0.4
    
    def _analyze_sentence_structure(self, source_name: str, target_name: str, predicate: str, context: str) -> float:
        """문장 구조를 분석합니다."""
        score = 0.5  # 기본 점수
        
        # 엔티티들이 같은 문장에 있는지 확인
        sentences = context.split('.')
        
        for sentence in sentences:
            if source_name in sentence and target_name in sentence:
                # 같은 문장에 있으면 높은 점수
                score += 0.3
                
                # 관계 키워드가 문장에 있으면 추가 점수
                relation_keywords = {
                    "COMPETES_WITH": ["경쟁", "라이벌"],
                    "COLLABORATES_WITH": ["협력", "파트너"],
                    "ACQUIRED": ["인수", "매입"],
                    "WORKS_FOR": ["근무", "소속"],
                    "LOCATED_IN": ["위치", "소재"]
                }
                
                keywords = relation_keywords.get(predicate, [])
                for keyword in keywords:
                    if keyword in sentence:
                        score += 0.2
                        break
                        
                break
        
        return min(1.0, score)
    
    def _get_type_base_confidence(self, spacy_label: str) -> float:
        """spaCy 라벨별 기본 신뢰도를 반환합니다."""
        type_confidences = {
            "PS": 0.8,   # Person
            "LC": 0.9,   # Location  
            "OG": 0.8,   # Organization
            "DT": 0.9,   # Date/Time
            "QT": 0.7,   # Quantity
            "CV": 0.6,   # Civilization
            "AM": 0.5,   # Artifact
            "AF": 0.5,   # Animal
            "PT": 0.5,   # Plant
            "TM": 0.4,   # Term
            "EV": 0.6,   # Event
        }
        return type_confidences.get(spacy_label, 0.5)
    
    def _matches_known_patterns(self, text: str) -> bool:
        """알려진 패턴과 매칭되는지 확인합니다."""
        import re
        
        patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 이메일
            r'https?://[^\s]+',  # URL
            r'\d{2,4}-\d{2,4}-\d{2,4}',  # 전화번호
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
                
        return False
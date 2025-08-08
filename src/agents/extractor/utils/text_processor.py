"""
Text Processor

텍스트 전처리를 담당하는 모듈
"""

import logging
import re
from typing import List, Optional, Dict


class TextProcessor:
    """텍스트 전처리기"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        TextProcessor 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
    def preprocess_text(self, text: str, options: Optional[dict] = None) -> str:
        """
        텍스트를 전처리합니다.
        
        Args:
            text: 원본 텍스트
            options: 전처리 옵션
            
        Returns:
            str: 전처리된 텍스트
        """
        if not text:
            return ""
            
        options = options or {}
        
        # 기본 전처리 단계들
        processed = text
        
        # 1. 불필요한 공백 제거
        if options.get("remove_extra_spaces", True):
            processed = self._remove_extra_spaces(processed)
            
        # 2. 특수문자 정규화
        if options.get("normalize_special_chars", True):
            processed = self._normalize_special_characters(processed)
            
        # 3. 문장 경계 정리
        if options.get("normalize_sentences", True):
            processed = self._normalize_sentence_boundaries(processed)
            
        # 4. 숫자 정규화
        if options.get("normalize_numbers", False):
            processed = self._normalize_numbers(processed)
            
        return processed
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할합니다.
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            List[str]: 문장 리스트
        """
        # 한국어 문장 종결 패턴
        sentence_endings = r'[.!?…]\s+'
        sentences = re.split(sentence_endings, text)
        
        # 빈 문장 제거 및 정리
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 1:
                cleaned_sentences.append(sentence)
                
        return cleaned_sentences
    
    def extract_keywords(self, text: str, min_length: int = 2) -> List[str]:
        """
        텍스트에서 키워드를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            min_length: 최소 키워드 길이
            
        Returns:
            List[str]: 키워드 리스트
        """
        # 한글, 영어, 숫자로 구성된 토큰 추출
        pattern = r'[가-힣A-Za-z0-9]+' 
        tokens = re.findall(pattern, text)
        
        # 길이 필터링 및 중복 제거
        keywords = []
        seen = set()
        for token in tokens:
            if len(token) >= min_length and token not in seen:
                keywords.append(token)
                seen.add(token)
                
        return keywords
    
    def extract_korean_entities(self, text: str) -> List[str]:
        """
        한국어 텍스트에서 잠재적 엔티티를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            List[str]: 잠재적 엔티티 리스트
        """
        entities = []
        
        # 1. 한국어 이름 패턴 (2-4글자)
        name_pattern = r'[가-힣]{2,4}(?:\s+[가-힣]{2,4})?'
        names = re.findall(name_pattern, text)
        entities.extend(names)
        
        # 2. 회사명 패턴
        company_pattern = r'[가-힣A-Za-z0-9]+(?:주식회사|회사|기업|그룹|재단|은행|대학|연구소)'
        companies = re.findall(company_pattern, text)
        entities.extend(companies)
        
        # 3. 지명 패턴
        location_pattern = r'[가-힣]+(?:시|군|구|읍|면|동|리)'
        locations = re.findall(location_pattern, text)
        entities.extend(locations)
        
        # 4. 직책 + 이름 패턴
        title_pattern = r'(?:대표|회장|사장|부장|과장|팀장|이사|상무|전무|CEO|CTO|CFO)\s+[가-힣]{2,4}'
        titles = re.findall(title_pattern, text)
        entities.extend(titles)
        
        # 중복 제거 및 정리
        unique_entities = []
        seen = set()
        for entity in entities:
            clean_entity = self.normalize_entity_name(entity)
            if clean_entity and clean_entity not in seen:
                unique_entities.append(clean_entity)
                seen.add(clean_entity)
                
        return unique_entities
    
    def extract_relation_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        텍스트에서 관계 키워드를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            Dict[str, List[str]]: 관계 타입별 키워드
        """
        relation_keywords = {
            "COMPETES_WITH": [],
            "COLLABORATES_WITH": [],
            "ACQUIRED": [],
            "SUBSIDIARY_OF": [],
            "WORKS_FOR": [],
            "LOCATED_IN": [],
            "BELONGS_TO": [],
            "MANUFACTURES": [],
            "INVESTED_IN": []
        }
        
        # 경쟁 관계 키워드
        competition_pattern = r'(경쟁|라이벌|대항|vs|대|상대)'
        relation_keywords["COMPETES_WITH"] = re.findall(competition_pattern, text)
        
        # 협력 관계 키워드
        collaboration_pattern = r'(협력|파트너십|제휴|공동|함께|연합)'
        relation_keywords["COLLABORATES_WITH"] = re.findall(collaboration_pattern, text)
        
        # 인수 관계 키워드
        acquisition_pattern = r'(인수|매입|합병|인수합병|M&A)'
        relation_keywords["ACQUIRED"] = re.findall(acquisition_pattern, text)
        
        # 소속 관계 키워드
        subsidiary_pattern = r'(자회사|계열사|지사|분사|하위)'
        relation_keywords["SUBSIDIARY_OF"] = re.findall(subsidiary_pattern, text)
        
        # 근무 관계 키워드
        employment_pattern = r'(근무|소속|재직|직원|사원|팀)'
        relation_keywords["WORKS_FOR"] = re.findall(employment_pattern, text)
        
        # 위치 관계 키워드
        location_pattern = r'(위치|소재|기반|본사|지점|사무소)'
        relation_keywords["LOCATED_IN"] = re.findall(location_pattern, text)
        
        # 제조 관계 키워드
        manufacture_pattern = r'(제조|생산|개발|만들다|제작)'
        relation_keywords["MANUFACTURES"] = re.findall(manufacture_pattern, text)
        
        # 투자 관계 키워드
        investment_pattern = r'(투자|자본|지원|후원|펀딩)'
        relation_keywords["INVESTED_IN"] = re.findall(investment_pattern, text)
        
        return relation_keywords
    
    def normalize_entity_name(self, name: str) -> str:
        """
        엔티티 이름을 정규화합니다.
        
        Args:
            name: 원본 엔티티 이름
            
        Returns:
            str: 정규화된 엔티티 이름
        """
        if not name:
            return ""
            
        # 앞뒤 공백 제거
        normalized = name.strip()
        
        # 연속된 공백을 하나로 통합
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 불필요한 구두점 제거 (문맥에 따라)
        normalized = re.sub(r'^[^\w가-힣]+|[^\w가-힣]+$', '', normalized)
        
        return normalized
    
    def _remove_extra_spaces(self, text: str) -> str:
        """연속된 공백을 제거합니다."""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _normalize_special_characters(self, text: str) -> str:
        """특수문자를 정규화합니다."""
        # 다양한 따옴표를 표준 따옴표로 통일
        text = re.sub(r'[""''``]', '"', text)
        
        # 다양한 대시를 하이픈으로 통일
        text = re.sub(r'[–—―]', '-', text)
        
        # 전각 문자를 반각으로 변환
        text = text.replace('　', ' ')  # 전각 공백
        
        return text
    
    def _normalize_sentence_boundaries(self, text: str) -> str:
        """문장 경계를 정규화합니다."""
        # 문장 끝 구두점 뒤에 공백 추가
        text = re.sub(r'([.!?…])([가-힣A-Za-z])', r'\1 \2', text)
        
        # 연속된 구두점 정리
        text = re.sub(r'[.]{2,}', '…', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text
    
    def _normalize_numbers(self, text: str) -> str:
        """숫자를 정규화합니다."""
        # 천 단위 콤마가 있는 숫자 정규화
        text = re.sub(r'(\d{1,3}(?:,\d{3})+)', lambda m: m.group(1).replace(',', ''), text)
        
        # 전각 숫자를 반각으로 변환
        full_to_half = str.maketrans('０１２３４５６７８９', '0123456789')
        text = text.translate(full_to_half)
        
        return text
    
    def extract_context_window(self, text: str, target: str, window_size: int = 50) -> str:
        """
        대상 문자열 주변의 컨텍스트 윈도우를 추출합니다.
        
        Args:
            text: 전체 텍스트
            target: 대상 문자열
            window_size: 윈도우 크기 (문자 수)
            
        Returns:
            str: 컨텍스트 윈도우
        """
        index = text.find(target)
        if index == -1:
            return ""
            
        start = max(0, index - window_size)
        end = min(len(text), index + len(target) + window_size)
        
        return text[start:end]
    
    def is_valid_entity_name(self, name: str) -> bool:
        """
        유효한 엔티티 이름인지 검증합니다.
        
        Args:
            name: 검증할 이름
            
        Returns:
            bool: 유효성 여부
        """
        if not name or len(name.strip()) < 2:
            return False
            
        # 너무 긴 이름 제외
        if len(name) > 100:
            return False
            
        # 숫자로만 구성된 경우 제외 (일반적인 엔티티가 아님)
        if name.isdigit():
            return False
            
        # 특수문자로만 구성된 경우 제외
        if re.match(r'^[^\w가-힣]+$', name):
            return False
            
        return True
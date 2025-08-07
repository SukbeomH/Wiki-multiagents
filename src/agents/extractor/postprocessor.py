"""
GPT 응답 후처리 로직

GPT-4o의 응답을 파싱하고 정규식으로 필드 보정 및 검증을 수행하는 후처리 로직
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.schemas.agents import Entity, Relation


class ExtractorPostprocessor:
    """GPT 응답 후처리 로직"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        후처리 로직 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 정규식 패턴 정의
        self.patterns = {
            "json_block": r'```json\s*(.*?)\s*```',
            "json_content": r'\{.*\}',
            "date_pattern": r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?',
            "money_pattern": r'(\d+(?:,\d{3})*)\s*(원|달러|유로|엔|위안|파운드)',
            "percent_pattern": r'(\d+(?:\.\d+)?)\s*%',
            "quantity_pattern": r'(\d+(?:\.\d+)?)\s*(개|명|마리|대|권|장|개월|년|시간|분|초|km|m|cm|kg|g|ml|l)',
            "time_pattern": r'(\d{1,2}):(\d{2})(?::(\d{2}))?',
            "year_pattern": r'(\d{4})년',
            "month_pattern": r'(\d{1,2})월',
            "day_pattern": r'(\d{1,2})일'
        }
        
        # 구조화된 로그 초기화
        self._log_structured("postprocessor_initialized")
    
    def _log_structured(self, event: str, **kwargs):
        """
        구조화된 JSON 로그 출력
        
        Args:
            event: 이벤트 이름
            **kwargs: 추가 로그 데이터
        """
        # Mock 객체나 직렬화할 수 없는 객체 처리
        safe_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(value, '__class__') and 'Mock' in value.__class__.__name__:
                safe_kwargs[key] = f"<{value.__class__.__name__}>"
            else:
                try:
                    # JSON 직렬화 테스트
                    json.dumps(value, ensure_ascii=False)
                    safe_kwargs[key] = value
                except (TypeError, ValueError):
                    safe_kwargs[key] = str(value)
        
        log_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **safe_kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        응답 텍스트에서 JSON 블록 추출
        
        Args:
            response_text: GPT 응답 텍스트
            
        Returns:
            Optional[Dict[str, Any]]: 추출된 JSON 데이터
        """
        self._log_structured("json_extraction_started", response_length=len(response_text))
        
        try:
            # 1. 코드 블록 내 JSON 추출 시도
            json_match = re.search(self.patterns["json_block"], response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                self._log_structured("json_block_found", json_length=len(json_str))
                return json.loads(json_str)
            
            # 2. 일반 JSON 객체 추출 시도
            json_match = re.search(self.patterns["json_content"], response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0).strip()
                self._log_structured("json_content_found", json_length=len(json_str))
                return json.loads(json_str)
            
            # 3. 전체 텍스트를 JSON으로 파싱 시도
            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                pass
            
            self._log_structured("json_extraction_failed", reason="no_valid_json_found")
            return None
            
        except json.JSONDecodeError as e:
            self._log_structured("json_parsing_error", error=str(e))
            return None
        except Exception as e:
            self._log_structured("json_extraction_error", error=str(e))
            return None
    
    def clean_and_validate_entities(self, entities: List[Dict[str, Any]], original_text: str) -> List[Entity]:
        """
        엔티티 데이터 정리 및 검증
        
        Args:
            entities: 원본 엔티티 데이터 리스트
            original_text: 원본 텍스트
            
        Returns:
            List[Entity]: 검증된 엔티티 리스트
        """
        cleaned_entities = []
        
        for i, entity_data in enumerate(entities):
            try:
                # 필수 필드 확인 및 기본값 설정
                entity_id = entity_data.get("id", f"e{i+1}")
                entity_type = entity_data.get("type", "MISC")
                entity_name = entity_data.get("name", "")
                start_pos = entity_data.get("start")
                end_pos = entity_data.get("end")
                confidence = entity_data.get("confidence", 0.5)
                
                # 엔티티 이름 정리
                entity_name = self._clean_entity_name(entity_name)
                if not entity_name:
                    continue
                
                # 위치 정보 검증 및 보정
                start_pos, end_pos = self._validate_positions(start_pos, end_pos, entity_name, original_text)
                
                # 확신도 검증 및 보정
                confidence = self._validate_confidence(confidence)
                
                # 엔티티 타입 정리
                entity_type = self._clean_entity_type(entity_type)
                
                # Entity 객체 생성
                entity = Entity(
                    id=entity_id,
                    type=entity_type,
                    name=entity_name,
                    start=start_pos,
                    end=end_pos,
                    confidence=confidence
                )
                
                cleaned_entities.append(entity)
                
            except Exception as e:
                self._log_structured("entity_cleaning_error", entity_index=i, error=str(e))
                continue
        
        self._log_structured("entities_cleaned", original_count=len(entities), cleaned_count=len(cleaned_entities))
        return cleaned_entities
    
    def clean_and_validate_relations(self, relations: List[Dict[str, Any]], entity_ids: List[str]) -> List[Relation]:
        """
        관계 데이터 정리 및 검증
        
        Args:
            relations: 원본 관계 데이터 리스트
            entity_ids: 유효한 엔티티 ID 리스트
            
        Returns:
            List[Relation]: 검증된 관계 리스트
        """
        cleaned_relations = []
        
        for i, relation_data in enumerate(relations):
            try:
                # 필수 필드 확인
                source = relation_data.get("source", "")
                target = relation_data.get("target", "")
                predicate = relation_data.get("predicate", "RELATED_TO")
                confidence = relation_data.get("confidence", 0.5)
                
                # 엔티티 ID 검증
                if source not in entity_ids or target not in entity_ids:
                    continue
                
                # 출발과 도착 엔티티가 다른지 확인
                if source == target:
                    continue
                
                # 관계 타입 정리
                predicate = self._clean_relation_type(predicate)
                
                # 확신도 검증 및 보정
                confidence = self._validate_confidence(confidence)
                
                # Relation 객체 생성
                relation = Relation(
                    source=source,
                    target=target,
                    predicate=predicate,
                    confidence=confidence
                )
                
                cleaned_relations.append(relation)
                
            except Exception as e:
                self._log_structured("relation_cleaning_error", relation_index=i, error=str(e))
                continue
        
        self._log_structured("relations_cleaned", original_count=len(relations), cleaned_count=len(cleaned_relations))
        return cleaned_relations
    
    def _clean_entity_name(self, name: str) -> str:
        """
        엔티티 이름 정리
        
        Args:
            name: 원본 엔티티 이름
            
        Returns:
            str: 정리된 엔티티 이름
        """
        if not name or not isinstance(name, str):
            return ""
        
        # 공백 제거 및 정규화
        name = name.strip()
        
        # 특수 문자 제거 (하이픈, 언더스코어는 유지)
        name = re.sub(r'[^\w\s\-_]', '', name)
        
        # 연속된 공백을 하나로
        name = re.sub(r'\s+', ' ', name)
        
        return name
    
    def _clean_entity_type(self, entity_type: str) -> str:
        """
        엔티티 타입 정리
        
        Args:
            entity_type: 원본 엔티티 타입
            
        Returns:
            str: 정리된 엔티티 타입
        """
        if not entity_type or not isinstance(entity_type, str):
            return "MISC"
        
        # 대문자로 변환
        entity_type = entity_type.upper().strip()
        
        # 유효한 엔티티 타입 목록
        valid_types = {
            "PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "EVENT",
            "DATE", "MONEY", "PERCENT", "QUANTITY", "TIME", "MISC"
        }
        
        if entity_type in valid_types:
            return entity_type
        
        # 유사한 타입 매핑
        type_mapping = {
            "COMPANY": "ORGANIZATION",
            "CORP": "ORGANIZATION",
            "ORG": "ORGANIZATION",
            "PLACE": "LOCATION",
            "CITY": "LOCATION",
            "COUNTRY": "LOCATION",
            "PERSON_NAME": "PERSON",
            "NAME": "PERSON",
            "CONCEPT": "CONCEPT",
            "IDEA": "CONCEPT",
            "EVENT": "EVENT",
            "OCCASION": "EVENT",
            "DATE_TIME": "DATE",
            "TIME": "TIME",
            "CURRENCY": "MONEY",
            "AMOUNT": "MONEY",
            "PERCENTAGE": "PERCENT",
            "RATIO": "PERCENT",
            "NUMBER": "QUANTITY",
            "MEASUREMENT": "QUANTITY"
        }
        
        return type_mapping.get(entity_type, "MISC")
    
    def _clean_relation_type(self, relation_type: str) -> str:
        """
        관계 타입 정리
        
        Args:
            relation_type: 원본 관계 타입
            
        Returns:
            str: 정리된 관계 타입
        """
        if not relation_type or not isinstance(relation_type, str):
            return "RELATED_TO"
        
        # 대문자로 변환
        relation_type = relation_type.upper().strip()
        
        # 유효한 관계 타입 목록
        valid_types = {
            "RELATED_TO", "PART_OF", "IS_A", "HAS_PROPERTY", "LOCATED_IN",
            "WORKS_FOR", "FOUNDED", "INVESTED_IN", "ACQUIRED", "COLLABORATES_WITH",
            "SIMILAR_TO", "OPPOSITE_OF", "CAUSES", "PREVENTS", "TREATS",
            "STUDIED_AT", "LIVES_IN", "BORN_IN", "DIED_IN", "CREATED"
        }
        
        if relation_type in valid_types:
            return relation_type
        
        # 유사한 타입 매핑
        type_mapping = {
            "RELATED": "RELATED_TO",
            "CONNECTED_TO": "RELATED_TO",
            "BELONGS_TO": "PART_OF",
            "MEMBER_OF": "PART_OF",
            "TYPE_OF": "IS_A",
            "KIND_OF": "IS_A",
            "HAS": "HAS_PROPERTY",
            "CONTAINS": "HAS_PROPERTY",
            "LOCATED": "LOCATED_IN",
            "IN": "LOCATED_IN",
            "EMPLOYED_BY": "WORKS_FOR",
            "EMPLOYEE_OF": "WORKS_FOR",
            "CREATED_BY": "FOUNDED",
            "ESTABLISHED": "FOUNDED",
            "INVESTMENT_IN": "INVESTED_IN",
            "BOUGHT": "ACQUIRED",
            "PURCHASED": "ACQUIRED",
            "COLLABORATES": "COLLABORATES_WITH",
            "PARTNERS_WITH": "COLLABORATES_WITH",
            "SIMILAR": "SIMILAR_TO",
            "LIKE": "SIMILAR_TO",
            "OPPOSITE": "OPPOSITE_OF",
            "AGAINST": "OPPOSITE_OF",
            "CAUSES": "CAUSES",
            "LEADS_TO": "CAUSES",
            "PREVENTS": "PREVENTS",
            "STOPS": "PREVENTS",
            "TREATS": "TREATS",
            "CURES": "TREATS",
            "STUDIED": "STUDIED_AT",
            "GRADUATED_FROM": "STUDIED_AT",
            "LIVES": "LIVES_IN",
            "RESIDES_IN": "LIVES_IN",
            "BORN": "BORN_IN",
            "DIED": "DIED_IN",
            "PASSED_AWAY_IN": "DIED_IN",
            "CREATED": "CREATED",
            "MADE": "CREATED",
            "BUILT": "CREATED"
        }
        
        return type_mapping.get(relation_type, "RELATED_TO")
    
    def _validate_positions(self, start: Optional[int], end: Optional[int], name: str, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        위치 정보 검증 및 보정
        
        Args:
            start: 시작 위치
            end: 끝 위치
            name: 엔티티 이름
            text: 원본 텍스트
            
        Returns:
            Tuple[Optional[int], Optional[int]]: 검증된 시작/끝 위치
        """
        # 위치 정보가 없는 경우 텍스트에서 검색
        if start is None or end is None:
            name_pos = text.find(name)
            if name_pos != -1:
                start = name_pos
                end = name_pos + len(name)
            else:
                return None, None
        
        # 위치 정보 검증
        if not isinstance(start, int) or not isinstance(end, int):
            return None, None
        
        if start < 0 or end < 0:
            return None, None
        
        if start >= len(text) or end > len(text):
            return None, None
        
        if start >= end:
            return None, None
        
        return start, end
    
    def _validate_confidence(self, confidence: Any) -> float:
        """
        확신도 검증 및 보정
        
        Args:
            confidence: 원본 확신도 값
            
        Returns:
            float: 검증된 확신도 (0.0-1.0)
        """
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            return 0.5
        
        # 범위 검증 및 보정
        if confidence < 0.0:
            return 0.0
        elif confidence > 1.0:
            return 1.0
        
        return confidence
    
    def process_gpt_response(self, response_text: str, original_text: str) -> Dict[str, Any]:
        """
        GPT 응답 전체 후처리
        
        Args:
            response_text: GPT 응답 텍스트
            original_text: 원본 텍스트
            
        Returns:
            Dict[str, Any]: 후처리된 결과
        """
        start_time = datetime.now()
        
        self._log_structured("postprocessing_started", response_length=len(response_text))
        
        try:
            # JSON 추출
            json_data = self.extract_json_from_response(response_text)
            if not json_data:
                return {
                    "status": "failed",
                    "error": "JSON 추출 실패",
                    "entities": [],
                    "relations": [],
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 엔티티 처리
            raw_entities = json_data.get("entities", [])
            cleaned_entities = self.clean_and_validate_entities(raw_entities, original_text)
            
            # 유효한 엔티티 ID 목록
            valid_entity_ids = [entity.id for entity in cleaned_entities]
            
            # 관계 처리
            raw_relations = json_data.get("relations", [])
            cleaned_relations = self.clean_and_validate_relations(raw_relations, valid_entity_ids)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "status": "success",
                "entities": cleaned_entities,
                "relations": cleaned_relations,
                "processing_time": processing_time,
                "original_entities_count": len(raw_entities),
                "original_relations_count": len(raw_relations),
                "cleaned_entities_count": len(cleaned_entities),
                "cleaned_relations_count": len(cleaned_relations)
            }
            
            self._log_structured(
                "postprocessing_completed",
                processing_time=processing_time,
                entities_count=len(cleaned_entities),
                relations_count=len(cleaned_relations)
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            error_result = {
                "status": "failed",
                "error": str(e),
                "entities": [],
                "relations": [],
                "processing_time": processing_time
            }
            
            self._log_structured("postprocessing_error", error=str(e), processing_time=processing_time)
            
            return error_result 
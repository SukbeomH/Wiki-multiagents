"""
Extractor Agent

엔티티·관계 추출을 담당하는 에이전트
- Azure GPT-4o 연동
- Regex 기반 후처리
- 엔티티 및 관계 추출
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.schemas.agents import ExtractorIn, ExtractorOut, Entity, Relation


class ExtractorAgent:
    """엔티티·관계 추출 에이전트"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        Extractor Agent 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 구조화된 로그 초기화
        self._log_structured(
            "extractor_agent_initialized",
            log_level=log_level
        )
    
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
    
    def extract(self, input_data: ExtractorIn) -> ExtractorOut:
        """
        문서에서 엔티티와 관계를 추출
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            ExtractorOut: 추출 결과
        """
        start_time = datetime.now()
        
        self._log_structured(
            "extraction_started",
            docs_count=len(input_data.docs),
            extraction_mode=input_data.extraction_mode,
            entity_types=input_data.entity_types,
            min_confidence=input_data.min_confidence
        )
        
        try:
            # TODO: 실제 추출 로직 구현
            # 1. Azure GPT-4o API 호출
            # 2. Regex 기반 후처리
            # 3. 엔티티 및 관계 추출
            
            # 임시 구현 (플레이스홀더)
            entities = []
            relations = []
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            processing_stats = {
                "total_docs": len(input_data.docs),
                "extraction_mode": input_data.extraction_mode,
                "entities_found": len(entities),
                "relations_found": len(relations),
                "avg_confidence": 0.0,
                "processing_time": processing_time
            }
            
            result = ExtractorOut(
                entities=entities,
                relations=relations,
                processing_stats=processing_stats
            )
            
            self._log_structured(
                "extraction_completed",
                entities_count=len(entities),
                relations_count=len(relations),
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self._log_structured(
                "extraction_failed",
                error=str(e),
                processing_time=processing_time
            )
            
            # 오류 시에도 유효한 ExtractorOut 반환
            processing_stats = {
                "total_docs": len(input_data.docs),
                "extraction_mode": input_data.extraction_mode,
                "entities_found": 0,
                "relations_found": 0,
                "avg_confidence": 0.0,
                "processing_time": processing_time,
                "error": str(e)
            }
            
            return ExtractorOut(
                entities=[],
                relations=[],
                processing_stats=processing_stats
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        에이전트 상태 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        start_time = datetime.now()
        
        try:
            # TODO: 실제 상태 확인 로직 구현
            # - Azure GPT-4o API 연결 상태
            # - 메모리 사용량
            # - 처리 성능 등
            
            health_info = {
                "status": "healthy",
                "agent_type": "extractor",
                "timestamp": datetime.now().isoformat(),
                "health_check_time": (datetime.now() - start_time).total_seconds(),
                "config": {
                    "extraction_modes": ["comprehensive", "fast", "focused"],
                    "supported_entity_types": ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "EVENT"],
                    "supported_languages": ["ko", "en", "ja", "zh"]
                }
            }
            
            self._log_structured(
                "health_check_completed",
                status="healthy",
                health_check_time=health_info["health_check_time"]
            )
            
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "agent_type": "extractor",
                "timestamp": datetime.now().isoformat(),
                "health_check_time": (datetime.now() - start_time).total_seconds(),
                "error": str(e)
            }
            
            self._log_structured(
                "health_check_failed",
                error=str(e),
                health_check_time=health_info["health_check_time"]
            )
            
            return health_info 
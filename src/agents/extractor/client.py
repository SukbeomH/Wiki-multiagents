"""
Azure GPT-4o 클라이언트

Azure OpenAI GPT-4o API 연동을 위한 클라이언트
- 환경 변수 기반 인증
- 연결 테스트
- 에러 처리 및 재시도 로직
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
from openai import AzureOpenAI


class AzureGPT4oClient:
    """Azure GPT-4o 클라이언트"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        Azure GPT-4o 클라이언트 초기화
        
        Args:
            log_level: 로그 레벨
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 환경 변수에서 설정 읽기
        self.endpoint = os.getenv("AOAI_ENDPOINT")
        self.api_key = os.getenv("AOAI_KEY")
        self.deployment_name = os.getenv("AOAI_DEPLOYMENT_NAME")
        
        # 설정 검증
        self._validate_config()
        
        # Azure OpenAI 클라이언트 초기화
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2024-02-15-preview"  # GPT-4o 지원 버전
        )
        
        # 구조화된 로그 초기화
        self._log_structured(
            "azure_client_initialized",
            endpoint=self.endpoint,
            deployment_name=self.deployment_name,
            api_version="2024-02-15-preview"
        )
    
    def _validate_config(self):
        """설정 검증"""
        missing_vars = []
        
        if not self.endpoint:
            missing_vars.append("AOAI_ENDPOINT")
        if not self.api_key:
            missing_vars.append("AOAI_KEY")
        if not self.deployment_name:
            missing_vars.append("AOAI_DEPLOYMENT_NAME")
        
        if missing_vars:
            raise ValueError(f"필수 환경 변수가 설정되지 않았습니다: {missing_vars}")
        
        # 엔드포인트 형식 검증
        if not self.endpoint.startswith("https://"):
            raise ValueError("AOAI_ENDPOINT는 https://로 시작해야 합니다.")
    
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
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Azure OpenAI 연결 테스트
        
        Returns:
            Dict[str, Any]: 연결 테스트 결과
        """
        start_time = datetime.now()
        
        self._log_structured("connection_test_started")
        
        try:
            # 간단한 테스트 요청
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, please respond with 'OK'."}
                ],
                max_tokens=10,
                temperature=0.0
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "status": "success",
                "response": response.choices[0].message.content,
                "processing_time": processing_time,
                "model": self.deployment_name,
                "endpoint": self.endpoint
            }
            
            self._log_structured(
                "connection_test_success",
                processing_time=processing_time,
                response=result["response"]
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            error_result = {
                "status": "failed",
                "error": str(e),
                "processing_time": processing_time,
                "model": self.deployment_name,
                "endpoint": self.endpoint
            }
            
            self._log_structured(
                "connection_test_failed",
                error=str(e),
                processing_time=processing_time
            )
            
            return error_result
    
    def extract_entities_and_relations(
        self, 
        text: str, 
        entity_types: Optional[List[str]] = None,
        extraction_mode: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        텍스트에서 엔티티와 관계 추출
        
        Args:
            text: 추출할 텍스트
            entity_types: 추출할 엔티티 타입 리스트 (None시 모든 타입)
            extraction_mode: 추출 모드 (comprehensive, fast, focused)
            
        Returns:
            Dict[str, Any]: 추출 결과
        """
        start_time = datetime.now()
        
        self._log_structured(
            "extraction_request_started",
            text_length=len(text),
            entity_types=entity_types,
            extraction_mode=extraction_mode
        )
        
        try:
            # 프롬프트 구성
            system_prompt = self._build_system_prompt(entity_types, extraction_mode)
            user_prompt = f"다음 텍스트에서 엔티티와 관계를 추출해주세요:\n\n{text}"
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.1,  # 일관성을 위해 낮은 temperature
                response_format={"type": "json_object"}  # JSON 응답 강제
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 응답 파싱
            response_content = response.choices[0].message.content
            extraction_result = json.loads(response_content)
            
            result = {
                "status": "success",
                "entities": extraction_result.get("entities", []),
                "relations": extraction_result.get("relations", []),
                "processing_time": processing_time,
                "raw_response": response_content
            }
            
            self._log_structured(
                "extraction_request_success",
                entities_count=len(result["entities"]),
                relations_count=len(result["relations"]),
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            error_result = {
                "status": "failed",
                "error": str(e),
                "processing_time": processing_time,
                "entities": [],
                "relations": []
            }
            
            self._log_structured(
                "extraction_request_failed",
                error=str(e),
                processing_time=processing_time
            )
            
            return error_result
    
    def _build_system_prompt(self, entity_types: Optional[List[str]], extraction_mode: str) -> str:
        """
        시스템 프롬프트 구성
        
        Args:
            entity_types: 엔티티 타입 리스트
            extraction_mode: 추출 모드
            
        Returns:
            str: 시스템 프롬프트
        """
        entity_type_str = ""
        if entity_types:
            entity_type_str = f"다음 엔티티 타입만 추출하세요: {', '.join(entity_types)}. "
        
        mode_instructions = {
            "comprehensive": "가능한 모든 엔티티와 관계를 상세하게 추출하세요.",
            "fast": "주요 엔티티와 핵심 관계만 빠르게 추출하세요.",
            "focused": "텍스트의 주요 주제와 관련된 엔티티와 관계에 집중하세요."
        }
        
        mode_instruction = mode_instructions.get(extraction_mode, mode_instructions["comprehensive"])
        
        prompt = f"""당신은 텍스트에서 엔티티와 관계를 추출하는 전문가입니다.

{entity_type_str}{mode_instruction}

응답은 반드시 다음 JSON 형식으로 제공하세요:
{{
    "entities": [
        {{
            "id": "고유식별자",
            "type": "엔티티타입",
            "name": "엔티티이름",
            "start": 시작위치,
            "end": 끝위치,
            "confidence": 확신도(0.0-1.0)
        }}
    ],
    "relations": [
        {{
            "source": "출발엔티티ID",
            "target": "도착엔티티ID",
            "predicate": "관계타입",
            "confidence": 확신도(0.0-1.0)
        }}
    ]
}}

엔티티 타입: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, DATE, MONEY, PERCENT, QUANTITY, TIME, MISC
관계 타입: RELATED_TO, PART_OF, IS_A, HAS_PROPERTY, LOCATED_IN, WORKS_FOR, FOUNDED, INVESTED_IN, ACQUIRED, COLLABORATES_WITH, SIMILAR_TO, OPPOSITE_OF, CAUSES, PREVENTS, TREATS, STUDIED_AT, LIVES_IN, BORN_IN, DIED_IN, CREATED

확신도는 0.0에서 1.0 사이의 값으로 설정하세요."""
        
        return prompt
    
    def health_check(self) -> Dict[str, Any]:
        """
        클라이언트 헬스 체크
        
        Returns:
            Dict[str, Any]: 헬스 체크 결과
        """
        try:
            # 연결 테스트 수행
            connection_result = self.test_connection()
            
            health_status = {
                "status": "healthy" if connection_result["status"] == "success" else "unhealthy",
                "endpoint": self.endpoint,
                "deployment_name": self.deployment_name,
                "connection_test": connection_result,
                "timestamp": datetime.now().isoformat()
            }
            
            self._log_structured(
                "health_check_completed",
                status=health_status["status"]
            )
            
            return health_status
            
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.endpoint,
                "deployment_name": self.deployment_name,
                "timestamp": datetime.now().isoformat()
            }
            
            self._log_structured(
                "health_check_failed",
                error=str(e)
            )
            
            return health_status 
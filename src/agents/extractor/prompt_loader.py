"""
프롬프트 템플릿 로더

엔티티·관계 추출을 위한 프롬프트 템플릿을 로드하고 관리하는 유틸리티
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class PromptLoader:
    """프롬프트 템플릿 로더"""
    
    def __init__(self, prompt_file: str = "extractor_prompt.json"):
        """
        프롬프트 로더 초기화
        
        Args:
            prompt_file: 프롬프트 파일명
        """
        self.prompt_file = prompt_file
        self.prompt_data = self._load_prompt_template()
    
    def _load_prompt_template(self) -> Dict[str, Any]:
        """
        프롬프트 템플릿 로드
        
        Returns:
            Dict[str, Any]: 프롬프트 템플릿 데이터
        """
        # 현재 파일의 디렉토리에서 prompts 폴더 찾기
        current_dir = Path(__file__).parent
        prompt_path = current_dir / "prompts" / self.prompt_file
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"프롬프트 파일 JSON 파싱 오류: {e}")
        except Exception as e:
            raise RuntimeError(f"프롬프트 파일 로드 오류: {e}")
    
    def get_system_prompt(
        self, 
        entity_types: Optional[List[str]] = None,
        extraction_mode: str = "comprehensive"
    ) -> str:
        """
        시스템 프롬프트 생성
        
        Args:
            entity_types: 엔티티 타입 리스트 (None시 모든 타입)
            extraction_mode: 추출 모드 (comprehensive, fast, focused)
            
        Returns:
            str: 시스템 프롬프트
        """
        system_data = self.prompt_data["system_prompt"]
        
        # 기본 프롬프트
        prompt_parts = [system_data["base"]]
        
        # 추출 모드별 지시사항
        if extraction_mode in system_data["instructions"]:
            prompt_parts.append(system_data["instructions"][extraction_mode])
        
        # 엔티티 타입 필터링
        if entity_types:
            entity_descriptions = []
            for entity_type in entity_types:
                if entity_type in system_data["entity_types"]:
                    entity_descriptions.append(f"{entity_type}: {system_data['entity_types'][entity_type]}")
            
            if entity_descriptions:
                prompt_parts.append(f"다음 엔티티 타입만 추출하세요:\n" + "\n".join(entity_descriptions))
        
        # 출력 형식
        prompt_parts.append(system_data["output_format"]["description"])
        
        # 엔티티 형식 예시
        entities_example = system_data["output_format"]["entities"]
        prompt_parts.append("엔티티 형식:")
        for entity in entities_example:
            prompt_parts.append(f"  - {entity['id']}: {entity['type']} 타입, 이름: {entity['name']}, 위치: {entity['start']}-{entity['end']}, 확신도: {entity['confidence']}")
        
        # 관계 형식 예시
        relations_example = system_data["output_format"]["relations"]
        prompt_parts.append("관계 형식:")
        for relation in relations_example:
            prompt_parts.append(f"  - {relation['source']} → {relation['target']}: {relation['predicate']} (확신도: {relation['confidence']})")
        
        # 엔티티 타입 목록
        entity_types_list = list(system_data["entity_types"].keys())
        prompt_parts.append(f"엔티티 타입: {', '.join(entity_types_list)}")
        
        # 관계 타입 목록
        relation_types_list = list(system_data["relation_types"].keys())
        prompt_parts.append(f"관계 타입: {', '.join(relation_types_list)}")
        
        # 확신도 가이드라인
        confidence_guidelines = system_data["confidence_guidelines"]
        prompt_parts.append("확신도 가이드라인:")
        for range_key, description in confidence_guidelines.items():
            prompt_parts.append(f"  - {range_key}: {description}")
        
        # 모범 사례
        best_practices = system_data["best_practices"]
        prompt_parts.append("모범 사례:")
        for practice in best_practices:
            prompt_parts.append(f"  - {practice}")
        
        return "\n\n".join(prompt_parts)
    
    def get_example_prompts(self) -> List[Dict[str, Any]]:
        """
        예시 프롬프트 목록 반환
        
        Returns:
            List[Dict[str, Any]]: 예시 프롬프트 목록
        """
        examples = self.prompt_data["examples"]
        example_prompts = []
        
        for example_name, example_data in examples.items():
            example_prompts.append({
                "name": example_name,
                "input": example_data["input"],
                "expected_output": example_data["expected_output"]
            })
        
        return example_prompts
    
    def get_entity_type_description(self, entity_type: str) -> Optional[str]:
        """
        엔티티 타입 설명 반환
        
        Args:
            entity_type: 엔티티 타입
            
        Returns:
            Optional[str]: 엔티티 타입 설명
        """
        entity_types = self.prompt_data["system_prompt"]["entity_types"]
        return entity_types.get(entity_type)
    
    def get_relation_type_description(self, relation_type: str) -> Optional[str]:
        """
        관계 타입 설명 반환
        
        Args:
            relation_type: 관계 타입
            
        Returns:
            Optional[str]: 관계 타입 설명
        """
        relation_types = self.prompt_data["system_prompt"]["relation_types"]
        return relation_types.get(relation_type)
    
    def get_error_handling_guidelines(self) -> Dict[str, str]:
        """
        에러 처리 가이드라인 반환
        
        Returns:
            Dict[str, str]: 에러 처리 가이드라인
        """
        return self.prompt_data["error_handling"]
    
    def validate_extraction_mode(self, mode: str) -> bool:
        """
        추출 모드 검증
        
        Args:
            mode: 추출 모드
            
        Returns:
            bool: 유효한 모드 여부
        """
        valid_modes = list(self.prompt_data["system_prompt"]["instructions"].keys())
        return mode in valid_modes
    
    def validate_entity_type(self, entity_type: str) -> bool:
        """
        엔티티 타입 검증
        
        Args:
            entity_type: 엔티티 타입
            
        Returns:
            bool: 유효한 타입 여부
        """
        valid_types = list(self.prompt_data["system_prompt"]["entity_types"].keys())
        return entity_type in valid_types
    
    def validate_relation_type(self, relation_type: str) -> bool:
        """
        관계 타입 검증
        
        Args:
            relation_type: 관계 타입
            
        Returns:
            bool: 유효한 타입 여부
        """
        valid_types = list(self.prompt_data["system_prompt"]["relation_types"].keys())
        return relation_type in valid_types 
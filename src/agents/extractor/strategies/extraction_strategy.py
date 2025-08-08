"""
Extraction Strategy

추상 전략 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import List, Tuple

from src.core.schemas.agents import ExtractorIn, Entity, Relation


class ExtractionStrategy(ABC):
    """추출 전략 추상 클래스"""
    
    @abstractmethod
    def extract(self, input_data: ExtractorIn) -> Tuple[List[Entity], List[Relation]]:
        """
        엔티티와 관계를 추출합니다.
        
        Args:
            input_data: 추출 입력 데이터
            
        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        전략 이름을 반환합니다.
        
        Returns:
            str: 전략 이름
        """
        pass
    
    @abstractmethod
    def get_expected_performance(self) -> dict:
        """
        예상 성능 지표를 반환합니다.
        
        Returns:
            dict: 성능 지표 (속도, 정확도 등)
        """
        pass
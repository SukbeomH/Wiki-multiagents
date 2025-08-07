"""
Extractor Agent

엔티티·관계 추출을 담당하는 에이전트
- Azure GPT-4o 연동
- Regex 기반 후처리
- 엔티티 및 관계 추출
"""

from .agent import ExtractorAgent

# 기본 인스턴스 생성
extractor_agent = ExtractorAgent()

__all__ = [
    "ExtractorAgent",
    "extractor_agent"
]
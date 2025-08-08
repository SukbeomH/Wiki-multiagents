"""
Extractor Agent (ext.md 기반 단순화 버전)

엔티티·관계 추출을 담당하는 에이전트
- spaCy: 한국어 엔티티 추출
- korre: 한국어 관계 추출 (전용 라이브러리)
- LangGraph: 워크플로우 관리 (선택적)
- 기존 테스트 케이스 완전 호환
"""

from .agent import ExtractorAgent

# 기본 인스턴스 생성
extractor_agent = ExtractorAgent()

__all__ = [
    "ExtractorAgent",
    "extractor_agent"
]
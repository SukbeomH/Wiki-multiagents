"""
AI Knowledge Graph System - Agents Package

이 패키지는 지식 그래프 구축을 위한 7개의 에이전트를 포함합니다:
- Research: 키워드 기반 문서 수집·캐싱
- Extractor: 엔티티·관계 추출·증분 업데이트
- Retriever: 유사 문서 선별·문맥 보강 (RAG)
- Wiki: Markdown 위키 작성·요약
- GraphViz: 지식 그래프 시각화
- Supervisor: 오케스트레이션·Lock·Retry
- Feedback: 사용자 피드백 수집·정제 루프
"""
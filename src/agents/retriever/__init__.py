"""
Retriever Agent

유사 문서 선별을 담당하는 에이전트
- FAISS IVF-HNSW 벡터 스토어
- 유사도 기반 문서 검색
- 문맥 보강
"""

from .agent import RetrieverAgent, get_retriever_agent

# 기본 인스턴스 생성
retriever_agent = get_retriever_agent()

__all__ = [
    "RetrieverAgent",
    "get_retriever_agent",
    "retriever_agent"
]
"""
출처 추적 및 인용 관리 모듈
"""
from typing import List
from langchain_core.documents import Document


def format_retriever_results(docs: List[Document]) -> str:
    """Retriever 결과를 출처 정보가 포함된 텍스트로 변환한다."""
    if not docs:
        return "검색 결과가 없습니다."

    sections = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        source = meta.get("source_filename", meta.get("source", "알 수 없음"))
        page = meta.get("page_number", "")
        page_str = f" (p.{page})" if page else ""

        sections.append(
            f"[문서 {i}] {source}{page_str}\n"
            f"{doc.page_content}"
        )

    return "\n\n---\n\n".join(sections)


def wrap_retriever_with_citation(retriever):
    """retriever.invoke 결과를 출처 포함 텍스트로 변환하는 래퍼 함수를 반환한다."""
    def invoke_with_citation(query: str) -> str:
        docs = retriever.invoke(query)
        return format_retriever_results(docs)
    return invoke_with_citation

import streamlit as st
from typing import List, Literal

# ddgs 우선 사용, 미존재 시 구 패키지로 폴백
try:
    from ddgs import DDGS  # 최신 패키지명
except ImportError:  # pragma: no cover
    try:
        from duckduckgo_search import DDGS  # 구 패키지명
    except Exception:  # 최종 안전장치
        DDGS = None  # type: ignore

# LangChain 조건부 import
try:
    from langchain.schema import Document, HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Document = None
    HumanMessage = None
    SystemMessage = None

from ..utils.config import get_llm


def improve_search_query(
    topic: str,
    role: Literal["PRO_AGENT", "CON_AGENT", "JUDGE_AGENT"] = "JUDGE_AGENT",
) -> List[str]:

    template = "'{topic}'에 대해 {perspective} 웹검색에 적합한 3개의 검색어를 제안해주세요. 각 검색어는 25자 이내로 작성하고 콤마로 구분하세요. 검색어만 제공하고 설명은 하지 마세요."

    perspective_map = {
        "PRO_AGENT": "찬성하는 입장을 뒷받침할 수 있는 사실과 정보를 찾고자 합니다.",
        "CON_AGENT": "반대하는 입장을 뒷받침할 수 있는 사실과 정보를 찾고자 합니다.",
        "JUDGE_AGENT": "객관적인 사실과 정보를 찾고자 합니다.",
    }

    prompt = template.format(topic=topic, perspective=perspective_map[role])

    messages = [
        SystemMessage(
            content="당신은 검색 전문가입니다. 주어진 주제에 대해 가장 관련성 높은 검색어를 제안해주세요."
        ),
        HumanMessage(content=prompt),
    ]

    # 스트리밍 응답 받기
    response = get_llm().invoke(messages)

    # ,로 구분된 검색어 추출
    suggested_queries = [q.strip() for q in response.content.split(",")]

    return suggested_queries[:3]


def get_search_content(
    improved_queries: List[str],
    language: str = "ko",
    max_results: int = 5,
) -> List[Document]:

    try:
        documents = []

        if DDGS is None:
            st.error("검색 모듈(ddgs/duckduckgo_search)을 사용할 수 없습니다.")
            return []

        ddgs_client = DDGS()

        # 언어 → 지역 코드 매핑 (기본: 전역)
        region_map = {
            "ko": "kr-kr",
            "en": "us-en",
            "ja": "jp-jp",
            "zh": "cn-zh",
        }
        region = region_map.get(language.lower(), "wt-wt")

        # 각 개선된 검색어에 대해 검색 수행
        for query in improved_queries:
            try:
                # 검색 수행
                results = list(
                    ddgs_client.text(
                        query,
                        region=region,
                        safesearch="moderate",
                        timelimit="y",  # 최근 1년 내 결과
                        max_results=max_results,
                    )
                )

                if not results:
                    continue

                # 검색 결과 처리
                for result in results:
                    title = result.get("title", "")
                    body = result.get("body", "")
                    url = result.get("href", "")

                    if body:
                        documents.append(
                            Document(
                                page_content=body,
                                metadata={
                                    "source": url,
                                    "section": "content",
                                    "topic": title,
                                    "query": query,
                                },
                            )
                        )

            except Exception as e:
                st.warning(f"검색 중 오류 발생: {str(e)}")

        return documents

    except Exception as e:
        st.error(f"검색 서비스 오류 발생: {str(e)}")
        return []

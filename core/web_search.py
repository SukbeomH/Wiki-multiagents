"""
웹 검색 도구 모듈
"""
import time
import streamlit as st
from typing import List, Dict, Any
from ddgs import DDGS
from core.logger import logger


class WebSearchTool:
    """웹 검색 기능을 제공하는 클래스"""
    
    def __init__(self, max_retries: int = 3, initial_retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
    
    def search(self, query: str, max_results: int = 5) -> str:
        """
        ddgs 라이브러리를 사용하여 DuckDuckGo 웹 검색을 수행하고 결과를 포맷팅합니다.
        재시도 로직과 폴백 메커니즘을 포함합니다.
        """
        # 웹검색 토글 확인
        if not st.session_state.get("web_search_enabled", True):
            return "웹검색이 비활성화되어 있습니다. 사이드바에서 웹검색을 활성화하세요."
        
        retry_delay = self.initial_retry_delay
        
        for attempt in range(self.max_retries):
            try:
                logger.info("[web-search] query='%s' (시도 %d/%d)", query, attempt + 1, self.max_retries)
                # SSL 인증서 검증 오류 해결을 위해 verify=False 설정
                with DDGS(verify=False) as ddgs:
                    # 안정적인 백엔드만 사용하여 인증서 오류 방지
                    results = [r for r in ddgs.text(query, max_results=max_results, backend="google,brave,duckduckgo")]
                    if not results:
                        logger.info("[web-search] 결과 0건")
                        return "검색 결과가 없습니다."
                    
                    formatted_results = self._format_results(results)
                    logger.info("[web-search] 결과 %d건", len(formatted_results))
                    return "\n".join(formatted_results)
                    
            except Exception as e:
                logger.warning("[web-search] 시도 %d/%d 실패: %s", attempt + 1, self.max_retries, e)
                if attempt < self.max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                else:
                    logger.exception("[web-search] 모든 시도 실패")
                    return f"웹 검색 중 오류가 발생했습니다: {e}"
        
        return "웹 검색을 완료할 수 없습니다."
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """검색 결과를 포맷팅합니다."""
        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(
                f"결과 {i}: {res['title']}\n"
                f"요약: {res['body']}\n"
                f"URL: {res['href']}\n---"
            )
        return formatted_results


# 전역 웹 검색 도구 인스턴스
web_search_tool = WebSearchTool()


def web_search_func(query: str, max_results: int = 5) -> str:
    """웹 검색 함수 (기존 인터페이스 유지)"""
    return web_search_tool.search(query, max_results) 
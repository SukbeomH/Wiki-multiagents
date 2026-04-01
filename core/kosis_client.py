"""
KOSIS 통계청 공공 데이터 API 클라이언트
API 문서: https://kosis.kr/openapi/
"""
import requests
from typing import Optional
from core.config import Config
from core.logger import logger


def search_kosis(query: str, org_id: str = "", tbl_id: str = "", max_results: int = 5) -> str:
    """KOSIS API로 통계 데이터를 검색한다.

    Args:
        query: 검색 키워드 (예: "소비자물가지수")
        org_id: 기관코드 (기본: 빈 문자열 — 전체 검색)
        tbl_id: 통계표ID (기본: 빈 문자열)
        max_results: 최대 결과 수

    Returns:
        포맷팅된 통계 데이터 문자열
    """
    if not Config.KOSIS_API_KEY:
        return "KOSIS API 키가 설정되지 않았습니다. .env에 KOSIS_API_KEY를 추가하세요."

    try:
        # KOSIS 통계 목록 조회 API
        list_url = "https://kosis.kr/openapi/statisticsList.do"
        params = {
            "method": "getList",
            "apiKey": Config.KOSIS_API_KEY,
            "vwCd": "MT_ZTITLE",
            "parentListId": "",
            "format": "json",
            "jsonVD": "Y",
            "searchKwd": query,
            "numOfRows": str(max_results),
        }

        resp = requests.get(list_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return f"'{query}'에 대한 KOSIS 통계 데이터를 찾지 못했습니다."

        results = []
        items = data if isinstance(data, list) else [data]
        for i, item in enumerate(items[:max_results], 1):
            title = item.get("TBL_NM", item.get("LIST_NM", "제목 없음"))
            org = item.get("ORG_NM", "")
            period = item.get("PRD_DE", "")
            results.append(
                f"[통계 {i}] {title}\n"
                f"  기관: {org}\n"
                f"  기간: {period}\n"
                f"  출처: KOSIS 국가통계포털"
            )

        logger.info("[kosis] 검색 완료: query='%s', results=%d", query, len(results))
        return "\n\n".join(results) if results else f"'{query}'에 대한 결과가 없습니다."

    except requests.RequestException as e:
        logger.warning("[kosis] API 요청 실패: %s", e)
        return f"KOSIS API 요청 중 오류가 발생했습니다: {e}"
    except Exception as e:
        logger.exception("[kosis] 처리 실패: %s", e)
        return f"KOSIS 데이터 처리 중 오류가 발생했습니다: {e}"

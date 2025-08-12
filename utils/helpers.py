"""
유틸리티 함수 모듈
"""
import os
import re
from typing import Dict, List
from dotenv import load_dotenv
from core.logger import logger


def setup_environment():
    """환경 변수를 로드하고 필수 변수가 설정되었는지 확인합니다."""
    load_dotenv()
    logger.info("[env] .env 로드 완료, 필수 환경변수 검증 시작")
    required_vars = ["AOAI_ENDPOINT", "AOAI_API_KEY", "AOAI_DEPLOY_GPT4O", "AOAI_DEPLOY_EMBED_3_LARGE"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error("[env] 필수 환경변수 누락: %s", var)
            raise ValueError(f"환경 변수 '{var}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    logger.info("[env] 필수 환경변수 검증 완료")


def extract_source_info(content: str) -> Dict[str, str]:
    """텍스트에서 출처 정보를 추출합니다."""
    
    source_info = {
        "source_name": "알 수 없음",
        "page_info": "",
        "evidence_text": content[:200] + "..." if len(content) > 200 else content,
        "confidence_score": "중간"
    }
    
    # PDF 파일명 추출 시도
    if "PDF" in content or ".pdf" in content.lower():
        pdf_match = re.search(r'([^/\\]+\.pdf)', content, re.IGNORECASE)
        if pdf_match:
            source_info["source_name"] = pdf_match.group(1)
    
    # 페이지 정보 추출 시도
    page_match = re.search(r'페이지\s*(\d+)', content)
    if page_match:
        source_info["page_info"] = f"페이지 {page_match.group(1)}"
    
    # URL 추출 시도
    url_match = re.search(r'https?://[^\s]+', content)
    if url_match:
        source_info["source_name"] = url_match.group(0)
        source_info["page_info"] = "웹 페이지"
    
    return source_info


def format_citations(sources: List[Dict[str, str]]) -> str:
    """출처 목록을 포맷팅된 인용 문자열로 변환합니다."""
    if not sources:
        return "출처 정보 없음"
    
    citations = []
    for i, source in enumerate(sources, 1):
        citation = f"📄 {source.get('source_name', '알 수 없음')} (p.{source.get('page_info', '')}) - 신뢰도: {source.get('confidence_score', '중간')}%"
        citations.append(f"{i}. {citation.strip()}")
    
    return "\n".join(citations)


def evaluate_evidence_quality(content: str, sources: List[Dict[str, str]]) -> Dict[str, int]:
    """근거의 품질을 평가합니다."""
    quality_score = 5  # 기본값
    reliability_score = 5
    recency_score = 5
    
    # 출처 수에 따른 품질 점수 조정
    if len(sources) >= 3:
        quality_score += 2
    elif len(sources) >= 1:
        quality_score += 1
    
    # 내용 길이에 따른 품질 점수 조정
    if len(content) > 500:
        quality_score += 1
    
    # 출처 신뢰성 평가
    for source in sources:
        source_name = source.get("source_name", "").lower()
        if "한국은행" in source_name or "bok" in source_name:
            reliability_score += 2
        elif "gov" in source_name or "정부" in source_name:
            reliability_score += 1
    
    # 점수 범위 제한
    quality_score = min(10, max(1, quality_score))
    reliability_score = min(10, max(1, reliability_score))
    recency_score = min(10, max(1, recency_score))
    
    return {
        "quality_score": quality_score,
        "reliability_score": reliability_score,
        "recency_score": recency_score
    }


def extract_preview_sources(content: str) -> List[str]:
    """응답 내용에서 근거 정보를 추출하여 미리보기용으로 반환합니다."""
    
    sources = []
    
    # 출처 정보 섹션 찾기
    source_patterns = [
        r'출처:\s*\[([^\]]+)\]\s*([^\n]+)',
        r'근거:\s*([^\n]+)',
        r'\[근거 및 출처\](.*?)(?=\n\[|\n$|$)',
        r'출처 정보\](.*?)(?=\n\[|\n$|$)'
    ]
    
    for pattern in source_patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                source_text = ' '.join(match).strip()
            else:
                source_text = match.strip()
            
            if source_text and len(source_text) > 10:
                # 텍스트 정리
                source_text = re.sub(r'\s+', ' ', source_text)
                source_text = source_text[:100] + "..." if len(source_text) > 100 else source_text
                sources.append(source_text)
    
    # 중복 제거 및 상위 3개 반환
    unique_sources = list(dict.fromkeys(sources))  # 순서 유지하면서 중복 제거
    return unique_sources[:3] 
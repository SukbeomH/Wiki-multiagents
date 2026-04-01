"""
사용자 피드백 수집 및 저장 모듈
"""
import json
import os
import time
from typing import Optional
from core.config import Config
from core.logger import logger


FEEDBACK_FILE = os.path.join(Config.DATA_DIR, "feedback.jsonl")


def save_feedback(
    query: str,
    response: str,
    rating: int,
    comment: Optional[str] = None,
) -> bool:
    """피드백을 JSONL 파일에 저장한다.

    Args:
        query: 사용자 질문
        response: AI 응답 (앞 500자만 저장)
        rating: 1(좋아요) 또는 0(싫어요)
        comment: 선택적 코멘트
    """
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "query": query[:200],
        "response_preview": response[:500],
        "rating": rating,
        "comment": comment,
    }
    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE) or ".", exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("[feedback] 저장 완료: rating=%d", rating)
        return True
    except Exception as e:
        logger.exception("[feedback] 저장 실패: %s", e)
        return False


def get_feedback_stats() -> dict:
    """피드백 통계를 반환한다."""
    if not os.path.exists(FEEDBACK_FILE):
        return {"total": 0, "positive": 0, "negative": 0}

    total = positive = 0
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += 1
                if record.get("rating") == 1:
                    positive += 1

    return {"total": total, "positive": positive, "negative": total - positive}

"""
분석 보고서 생성 모듈
"""
import time
from typing import List, Optional
from core.logger import logger


def generate_report(
    query: str,
    response: str,
    sources: List[dict],
    chart_titles: Optional[List[str]] = None,
) -> str:
    """분석 결과를 Markdown 보고서로 생성한다."""
    timestamp = time.strftime("%Y-%m-%d %H:%M")

    report = f"""# AI 경제 분석 보고서

**생성일시:** {timestamp}
**분석 질문:** {query}

---

## 분석 결과

{response}

---

## 출처 정보

"""
    if sources:
        for i, src in enumerate(sources, 1):
            if src["type"] == "pdf":
                page_str = f" p.{src['page']}" if src.get("page") else ""
                report += f"{i}. 📄 {src['name']}{page_str}\n"
            elif src["type"] == "web":
                report += f"{i}. 🌐 {src['name']}\n"
            else:
                report += f"{i}. {src['name']}\n"
    else:
        report += "출처 정보 없음\n"

    if chart_titles:
        report += "\n---\n\n## 시각화\n\n"
        for title in chart_titles:
            report += f"- 📊 {title}\n"
        report += "\n*(차트는 앱 내에서 확인하세요)*\n"

    report += """
---

*AI 한국은행 경제 분석팀 자동 생성 보고서*
"""
    logger.info("[report] 보고서 생성 완료: %d자", len(report))
    return report

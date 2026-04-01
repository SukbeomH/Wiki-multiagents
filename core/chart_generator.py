"""
차트 생성 모듈 — LLM이 생성한 JSON 데이터를 plotly 차트로 변환
"""
import json
import re
from typing import Optional
import plotly.graph_objects as go
from core.logger import logger


def extract_chart_data(text: str) -> Optional[dict]:
    """LLM 응답에서 ```chart_data ... ``` 블록을 파싱한다.

    Expected format:
    ```chart_data
    {
      "title": "기준금리 추이",
      "type": "line",
      "x": ["2024-01", "2024-04", "2024-07"],
      "y": [3.5, 3.5, 3.25],
      "x_label": "날짜",
      "y_label": "금리(%)"
    }
    ```
    """
    pattern = r"```chart_data\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        logger.info("[chart] chart_data 파싱 성공: type=%s", data.get("type"))
        return data
    except json.JSONDecodeError as e:
        logger.warning("[chart] chart_data JSON 파싱 실패: %s", e)
        return None


def create_chart(data: dict) -> Optional[go.Figure]:
    """파싱된 데이터로 plotly Figure를 생성한다."""
    chart_type = data.get("type", "line")
    title = data.get("title", "")
    x = data.get("x", [])
    y = data.get("y", [])
    x_label = data.get("x_label", "")
    y_label = data.get("y_label", "")

    if not x or not y:
        logger.warning("[chart] x 또는 y 데이터가 비어있음")
        return None

    fig = go.Figure()

    if chart_type == "bar":
        fig.add_trace(go.Bar(x=x, y=y, name=title))
    elif chart_type == "scatter":
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name=title))
    else:  # default: line
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=title))

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
    )
    logger.info("[chart] 차트 생성 완료: %s", title)
    return fig

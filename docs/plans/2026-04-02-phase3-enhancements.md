# Phase 3 Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 대화 히스토리 연속 분석, 멀티시리즈 차트, PDF 출처 딥링크, 분석 보고서 다운로드 4개 기능을 구현한다.

**Architecture:** 기존 LangGraph 그래프의 `stream()` 호출에 대화 히스토리를 주입하고, chart_generator를 멀티시리즈로 확장하며, 사이드바에 PDF 뷰어와 보고서 다운로드 기능을 추가한다. 모든 변경은 기존 모듈 패턴을 따라 최소 침습으로 구현한다.

**Tech Stack:** Python 3.9+, Streamlit, LangGraph, LangChain, plotly, base64(PDF embed)

**현재 코드베이스 핵심 포인트:**
- `app.py:542-544` — `stream()` 호출 시 `[HumanMessage(content=prompt)]`만 전달 (히스토리 없음)
- `app.py:33-34` — `AgentState`에 `messages` 필드만 존재
- `core/chart_generator.py` — 단일 x/y만 지원, `series` 미지원
- `core/state_manager.py` — `MESSAGES` 리스트로 대화 히스토리 관리 중
- `components/chat_interface.py:43-55` — `render_evidence_preview`에서 출처 렌더링
- `components/sidebar.py:108-118` — PDF 파일 목록 표시 (링크 없음)

---

## Feature 1: 대화 히스토리 기반 연속 분석

### Task 1.1: stream() 호출에 대화 히스토리 주입

**Files:**
- Modify: `app.py:527-544` (prompt 처리 및 stream 호출 부분)

**What to do:**

현재 `stream()`은 매번 새 `[HumanMessage(content=prompt)]`만 전달한다. 이전 대화 히스토리를 LangChain 메시지 객체로 변환하여 함께 전달한다.

**현재 코드 (app.py:542-544):**
```python
for chunk in StateManager.get_agent_graph().stream(
    {"messages": [HumanMessage(content=prompt)]},
    config={"recursion_limit": Config.MAX_ITERATIONS},
```

**변경 코드:**
```python
# 대화 히스토리를 LangChain 메시지로 변환
from langchain_core.messages import HumanMessage, AIMessage
history_messages = []
for msg in StateManager.get_messages()[:-1]:  # 마지막(현재) 메시지 제외
    if msg["role"] == "user":
        history_messages.append(HumanMessage(content=msg["content"]))
    elif msg["role"] == "assistant":
        history_messages.append(AIMessage(content=msg["content"]))

# 최근 N턴만 포함 (토큰 제한 방지)
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))
if len(history_messages) > MAX_HISTORY_TURNS * 2:
    history_messages = history_messages[-(MAX_HISTORY_TURNS * 2):]

all_messages = history_messages + [HumanMessage(content=prompt)]

for chunk in StateManager.get_agent_graph().stream(
    {"messages": all_messages},
    config={"recursion_limit": Config.MAX_ITERATIONS},
```

**주의:** `AIMessage` import를 app.py 상단 import에 추가해야 한다. 현재 `from langchain_core.messages import HumanMessage`만 있다 (line 9).

**Step 1: app.py 상단 import 수정**

```python
# app.py:9 변경
from langchain_core.messages import HumanMessage, AIMessage
```

**Step 2: stream() 호출 부분 변경 (app.py:527-544)**

위 코드 블록으로 교체.

**Step 3: Config에 MAX_HISTORY_TURNS 추가**

```python
# core/config.py 애플리케이션 설정 섹션에 추가
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))
```

**Step 4: Commit**

```bash
git add app.py core/config.py
git commit -m "feat: 대화 히스토리를 LangGraph에 주입하여 연속 분석 지원"
```

---

### Task 1.2: Supervisor 프롬프트에 대화 맥락 안내 추가

**Files:**
- Modify: `app.py:152-171` (create_supervisor 내 system_prompt)

**What to do:**

Supervisor가 이전 대화 맥락을 인식하도록 시스템 프롬프트에 안내를 추가한다.

**변경:** `create_supervisor` 내 system_prompt의 `**라우팅 기준:**` 앞에 추가:

```python
"**대화 맥락:**\n"
"- 이전 대화 히스토리가 messages에 포함될 수 있습니다\n"
"- 사용자가 '아까', '위에서', '이전에' 등으로 이전 대화를 참조하면 맥락을 활용하세요\n"
"- 새로운 주제의 질문이면 이전 맥락을 무시하세요\n\n"
```

**Step 1: system_prompt 수정**

**Step 2: Commit**

```bash
git add app.py
git commit -m "feat: Supervisor 프롬프트에 대화 맥락 인식 안내 추가"
```

---

## Feature 2: 멀티시리즈 차트

### Task 2.1: chart_generator에 멀티시리즈 지원 추가

**Files:**
- Modify: `core/chart_generator.py`

**What to do:**

기존 단일 x/y 외에 `series` 키를 지원하도록 확장. 하위 호환성을 유지한다.

**새 스키마 (기존과 공존):**
```json
{
  "title": "경제지표 비교",
  "type": "line",
  "x": ["2024-Q1", "2024-Q2", "2024-Q3"],
  "series": [
    {"name": "GDP 성장률", "y": [2.1, 2.3, 2.0]},
    {"name": "물가상승률", "y": [3.2, 2.8, 2.5]}
  ],
  "x_label": "분기",
  "y_label": "%"
}
```

**변경 코드 — `create_chart` 함수 전체 교체:**

```python
def create_chart(data: dict) -> Optional[go.Figure]:
    """파싱된 데이터로 plotly Figure를 생성한다. 단일시리즈/멀티시리즈 모두 지원."""
    chart_type = data.get("type", "line")
    title = data.get("title", "")
    x = data.get("x", [])
    x_label = data.get("x_label", "")
    y_label = data.get("y_label", "")

    # 멀티시리즈 또는 단일시리즈 판별
    series_list = data.get("series")
    if not series_list:
        # 단일시리즈 (하위 호환)
        y = data.get("y", [])
        if not x or not y:
            logger.warning("[chart] x 또는 y 데이터가 비어있음")
            return None
        series_list = [{"name": title, "y": y}]

    if not x:
        logger.warning("[chart] x 데이터가 비어있음")
        return None

    fig = go.Figure()

    for series in series_list:
        name = series.get("name", "")
        y = series.get("y", [])
        if not y:
            continue

        if chart_type == "bar":
            fig.add_trace(go.Bar(x=x, y=y, name=name))
        elif chart_type == "scatter":
            fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name=name))
        else:
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name))

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
    )
    logger.info("[chart] 차트 생성 완료: %s (%d series)", title, len(series_list))
    return fig
```

**Step 1: create_chart 함수 교체**

**Step 2: Analyst 프롬프트에 멀티시리즈 안내 추가**

`app.py`의 analyst_system_prompt 내 chart_data 형식 설명에 멀티시리즈 예시를 추가:

```
여러 지표를 비교할 때는 series를 사용하세요:
```chart_data
{
  "title": "경제지표 비교",
  "type": "line",
  "x": ["Q1", "Q2", "Q3"],
  "series": [
    {"name": "GDP", "y": [2.1, 2.3, 2.0]},
    {"name": "CPI", "y": [3.2, 2.8, 2.5]}
  ],
  "x_label": "분기",
  "y_label": "%"
}
```
```

**Step 3: Commit**

```bash
git add core/chart_generator.py app.py
git commit -m "feat: 멀티시리즈 차트 지원 — series 배열로 여러 지표 비교 가능"
```

---

## Feature 3: PDF 출처 딥링크

### Task 3.1: 출처 렌더링에 PDF 페이지 뷰어 링크 추가

**Files:**
- Modify: `components/chat_interface.py:43-55` (render_evidence_preview)
- Modify: `components/sidebar.py:108-118` (PDF 파일 목록)

**What to do:**

출처 정보의 PDF 항목에 "페이지 보기" 버튼을 추가한다. 클릭 시 Streamlit expander 안에 해당 PDF의 해당 페이지를 iframe으로 표시한다.

**주의:** Streamlit에서 PDF를 직접 보여주려면 base64 인코딩된 PDF를 `<iframe>` 또는 `st.components.v1.html`로 렌더링한다. 페이지 지정은 PDF.js의 `#page=N` 프래그먼트로 가능하다.

**Step 1: PDF 뷰어 유틸리티 함수 생성**

`components/common.py`에 PDF 뷰어 함수 추가:

```python
import base64
import os
import streamlit as st
import streamlit.components.v1 as components
from core.config import Config


def render_pdf_page(filename: str, page: int = 1, height: int = 500):
    """PDF 파일의 특정 페이지를 iframe으로 렌더링한다."""
    pdf_path = os.path.join(Config.DATA_DIR, filename)
    if not os.path.exists(pdf_path):
        st.warning(f"파일을 찾을 수 없습니다: {filename}")
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_url = f"data:application/pdf;base64,{b64}#page={page}"
    components.html(
        f'<iframe src="{pdf_url}" width="100%" height="{height}" type="application/pdf"></iframe>',
        height=height + 10,
    )
```

**Step 2: render_evidence_preview에서 PDF 소스에 뷰어 버튼 추가**

`components/chat_interface.py`의 PDF 렌더링 부분을 수정:

```python
# components/chat_interface.py — render_evidence_preview 내 PDF 분기
from components.common import render_pdf_page

def render_evidence_preview(final_response):
    """근거 미리보기를 렌더링합니다."""
    preview_sources = extract_preview_sources(final_response)
    if preview_sources:
        with st.expander("📋 출처 정보", expanded=True):
            for i, source in enumerate(preview_sources, 1):
                if source["type"] == "pdf":
                    page_str = f" p.{source['page']}" if source.get("page") else ""
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{i}.** 📄 {source['name']}{page_str}")
                    with col2:
                        if source.get("page"):
                            btn_key = f"pdf_view_{i}_{source['name']}_{source['page']}"
                            if st.button("📖 보기", key=btn_key):
                                render_pdf_page(source["name"], int(source["page"]))
                elif source["type"] == "web":
                    st.markdown(f"**{i}.** 🌐 [{source['name']}]({source['name']})")
                else:
                    st.markdown(f"**{i}.** {source['name']}")
```

**Step 3: 사이드바 PDF 목록에도 뷰어 기능 추가**

`components/sidebar.py`의 PDF 파일 목록 부분(108-118줄)을 수정:

```python
# components/sidebar.py — PDF 파일 목록 수정
if pdf_files_in_data:
    with st.container():
        st.write(f"**총 {len(pdf_files_in_data)}개 파일:**")
        for f_path in pdf_files_in_data:
            fname = os.path.basename(f_path)
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {fname}")
            with col2:
                if st.button("📖", key=f"sidebar_pdf_{fname}", help=f"{fname} 미리보기"):
                    from components.common import render_pdf_page
                    render_pdf_page(fname)
```

**Step 4: Commit**

```bash
git add components/common.py components/chat_interface.py components/sidebar.py
git commit -m "feat: PDF 출처 딥링크 — 페이지 번호 클릭으로 PDF 뷰어 표시"
```

---

## Feature 4: 분석 보고서 다운로드

### Task 4.1: 보고서 생성 모듈

**Files:**
- Create: `core/report_generator.py`

**What to do:**

최종 분석 결과 + 차트 + 출처 정보를 Markdown 보고서로 생성하는 모듈.

```python
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

    report += f"""
---

*AI 한국은행 경제 분석팀 자동 생성 보고서*
"""
    logger.info("[report] 보고서 생성 완료: %d자", len(report))
    return report
```

**Step 1: core/report_generator.py 생성**

**Step 2: Commit**

```bash
git add core/report_generator.py
git commit -m "feat: Markdown 분석 보고서 생성 모듈 추가"
```

---

### Task 4.2: 채팅 인터페이스에 보고서 다운로드 버튼 추가

**Files:**
- Modify: `app.py:690-710` (최종 응답 렌더링 후)

**What to do:**

최종 응답 표시 후, 피드백 위젯 전에 보고서 다운로드 버튼을 추가한다.

**현재 위치 (app.py:692-710 부근):**
```python
render_evidence_preview(final_response)
# 차트 렌더링 ...
st.success("✅ 분석 완료!")
# except ...
st.write(final_response)
# 피드백 위젯 ...
```

**추가 코드 — `st.write(final_response)` 직후, 피드백 위젯 직전:**

```python
st.write(final_response)
logger.info("[run] 최종 응답 길이=%d", len(final_response))

# 보고서 다운로드 버튼
from core.report_generator import generate_report
from utils.helpers import extract_preview_sources
report_sources = extract_preview_sources(final_response)
chart_titles = []
if "pending_charts" in st.session_state:
    # 이미 렌더링 후 클리어되었으므로 차트 제목은 응답에서 추출
    import re
    for m in re.finditer(r'"title":\s*"([^"]+)"', final_response):
        chart_titles.append(m.group(1))

last_query = ""
for msg in reversed(StateManager.get_messages()):
    if msg["role"] == "user":
        last_query = msg["content"]
        break

report_md = generate_report(last_query, final_response, report_sources, chart_titles or None)
timestamp = __import__("time").strftime("%Y%m%d_%H%M%S")
st.download_button(
    label="📥 보고서 다운로드",
    data=report_md,
    file_name=f"경제분석보고서_{timestamp}.md",
    mime="text/markdown",
    key=f"report_dl_{StateManager.get_feedback_index()}",
)

# 피드백 위젯
```

**Step 1: app.py에 보고서 다운로드 버튼 추가**

**Step 2: Commit**

```bash
git add app.py
git commit -m "feat: 분석 보고서 Markdown 다운로드 버튼 추가"
```

---

## 마무리

### Task 5.1: README 업데이트

**Files:**
- Modify: `README.md`

**Step 1: 변경 이력에 v2.4 추가**

```markdown
### v2.4 (최신) - Phase 3 기능 추가
- ✅ **대화 히스토리 연속 분석**: 이전 대화 맥락을 활용한 연속 질문 지원
- ✅ **멀티시리즈 차트**: 여러 경제 지표를 하나의 차트에서 비교 분석
- ✅ **PDF 출처 딥링크**: 출처의 페이지 번호 클릭으로 PDF 해당 페이지 즉시 열람
- ✅ **분석 보고서 다운로드**: 분석 결과를 Markdown 보고서로 내보내기
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: v2.4 Phase 3 기능 추가 변경 이력 업데이트"
```

---

## 요약

| Feature | Tasks | 신규 파일 | 수정 파일 |
|---|---|---|---|
| 1. 대화 히스토리 | 1.1, 1.2 | — | `app.py`, `core/config.py` |
| 2. 멀티시리즈 차트 | 2.1 | — | `core/chart_generator.py`, `app.py` |
| 3. PDF 딥링크 | 3.1 | — | `components/common.py`, `components/chat_interface.py`, `components/sidebar.py` |
| 4. 보고서 다운로드 | 4.1, 4.2 | `core/report_generator.py` | `app.py` |
| 5. 마무리 | 5.1 | — | `README.md` |

**총 7개 Task, 1개 신규 파일, 8개 수정 파일**

# Phase 2 Master Plan - AI 한국은행 경제 분석팀

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** PRD Phase 2의 4개 기능(답변 출처 명시, 사용자 피드백, 차트 생성 에이전트, 공공 데이터 연동)을 순서대로 구현한다.

**Architecture:** 기존 LangGraph Supervisor-Worker 아키텍처 위에 점진적으로 기능을 추가한다. 각 기능은 독립적인 모듈로 구현하여 기존 코드에 최소한의 변경만 가한다. RAG 파이프라인의 Document metadata를 활용하여 출처 추적을 강화하고, StateManager를 확장하여 피드백과 차트 상태를 관리한다.

**Tech Stack:** Python 3.9+, Streamlit, LangGraph, LangChain, FAISS, PyMuPDF, plotly, requests

**현재 코드베이스 요약:**
- `app.py` (645줄): 메인 앱, AgentState, create_agent, agent_node, create_supervisor, create_graph, main
- `core/rag_pipeline.py` (267줄): RAGPipeline 클래스, build_pipeline, create_*_retriever
- `core/config.py` (186줄): Config 클래스, 환경변수 관리
- `core/state_manager.py` (156줄): StateManager 클래스, 세션 상태 중앙 관리
- `core/web_search.py` (73줄): WebSearchTool 클래스
- `core/model_factory.py` (54줄): AzureModelFactory 클래스
- `components/sidebar.py` (125줄): 사이드바 UI
- `components/chat_interface.py` (78줄): 채팅 UI, render_evidence_preview
- `utils/helpers.py` (131줄): extract_source_info, format_citations, extract_preview_sources
- 테스트 없음, docs 디렉토리 신규 생성

---

## Feature 1: 답변 출처 명시 강화

### Task 1.1: RAG Document metadata에 페이지 번호 보존

**Files:**
- Modify: `core/rag_pipeline.py:219-225` (`_build_new_index` 내 PDF 로드 루프)

**Step 1: PyMuPDFLoader가 이미 page metadata를 포함하는지 확인**

PyMuPDFLoader는 기본적으로 `metadata.page` 필드를 포함한다. 현재 코드는 이를 활용하지 않고 있다. 확인 후 다음 단계에서 metadata 보존을 보장한다.

Run: `python3 -c "from langchain_community.document_loaders import PyMuPDFLoader; print('PyMuPDFLoader imported OK')"`
Expected: PyMuPDFLoader imported OK

**Step 2: _build_new_index에서 source metadata 보강**

`core/rag_pipeline.py`의 `_build_new_index` 메서드에서 로드된 문서의 metadata에 `source_filename` 필드를 명시적으로 추가한다.

```python
# core/rag_pipeline.py _build_new_index 내 PDF 로드 루프 (219-225줄 부근)
for pdf_path in pdf_files:
    try:
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_filename"] = os.path.basename(pdf_path)
            # PyMuPDFLoader는 'page' 키를 0-indexed로 제공 → 1-indexed로 변환
            if "page" in doc.metadata:
                doc.metadata["page_number"] = doc.metadata["page"] + 1
        all_docs.extend(docs)
        logger.info("[rag] 로드 완료: %s (%d pages)", os.path.basename(pdf_path), len(docs))
    except Exception as e:
        logger.exception("[rag] 로드 실패: %s", os.path.basename(pdf_path))
        st.sidebar.error(f"'{os.path.basename(pdf_path)}' 파일 로드 실패: {e}")
```

**Step 3: 앱 실행하여 metadata 보존 확인**

Run: `streamlit run app.py` (수동 확인 — PDF 업로드 후 로그에서 metadata 확인)

**Step 4: Commit**

```bash
git add core/rag_pipeline.py
git commit -m "feat: RAG 문서 metadata에 source_filename, page_number 보존"
```

---

### Task 1.2: Retriever 결과에서 출처 정보를 구조화하여 반환

**Files:**
- Create: `core/citation.py`
- Modify: `app.py:196-218` (`create_graph` 내 researcher_tools 정의)

**Step 1: citation 모듈 생성**

`core/citation.py`에 retriever 결과를 출처 정보가 포함된 포맷으로 변환하는 함수를 작성한다.

```python
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
```

**Step 2: create_graph에서 citation 래퍼 적용**

`app.py`의 `create_graph` 함수에서 researcher_tools의 `bok_document_search`와 `relaxed_document_search`에 citation 래퍼를 적용한다.

```python
# app.py create_graph 함수 상단에 import 추가
from core.citation import wrap_retriever_with_citation

# researcher_tools 정의 변경 (기존 196-201줄)
researcher_tools = [
    Tool(
        name="bok_document_search",
        func=wrap_retriever_with_citation(retriever),
        description="사용자가 업로드한 PDF 문서나 한국은행 공식 문서를 검색하여 특정 경제 용어, 정책, 보고서 내용을 찾습니다. 결과에 문서명과 페이지 번호가 포함됩니다."
    ),
    Tool(
        name="web_search",
        func=web_search_func,
        description="최신 경제 뉴스나 실시간 시장 반응 등 현재 정보를 위해 웹을 검색합니다."
    ),
]

# relaxed_retriever에도 동일 적용 (기존 214-218줄)
if relaxed_retriever:
    researcher_tools.append(
        Tool(
            name="relaxed_document_search",
            func=wrap_retriever_with_citation(relaxed_retriever),
            description="유사도 제한을 완화하여 더 넓은 범위에서 관련 문서를 검색합니다. 결과에 문서명과 페이지 번호가 포함됩니다."
        )
    )
```

**Step 3: core/__init__.py에 citation 모듈 export 추가**

```python
# core/__init__.py에 추가
from core.citation import wrap_retriever_with_citation
```

**Step 4: Commit**

```bash
git add core/citation.py core/__init__.py app.py
git commit -m "feat: RAG 검색 결과에 문서명/페이지 번호 포함 출처 추적 구현"
```

---

### Task 1.3: 최종 응답에서 출처 정보 렌더링 개선

**Files:**
- Modify: `utils/helpers.py:102-131` (`extract_preview_sources`)
- Modify: `components/chat_interface.py:43-51` (`render_evidence_preview`)

**Step 1: extract_preview_sources 개선 — 구조화된 출처 파싱**

```python
# utils/helpers.py — extract_preview_sources 함수 교체
def extract_preview_sources(content: str) -> List[Dict[str, str]]:
    """응답 내용에서 출처 정보를 구조화하여 추출한다."""
    sources = []

    # [문서 N] filename.pdf (p.X) 패턴 매칭
    doc_pattern = r'\[문서\s*\d+\]\s*([^\n(]+?)(?:\s*\(p\.(\d+)\))?'
    for match in re.finditer(doc_pattern, content):
        source_name = match.group(1).strip()
        page = match.group(2)
        sources.append({
            "type": "pdf",
            "name": source_name,
            "page": page,
        })

    # URL 패턴 매칭
    url_pattern = r'URL:\s*(https?://[^\s]+)'
    for match in re.finditer(url_pattern, content):
        sources.append({
            "type": "web",
            "name": match.group(1),
            "page": None,
        })

    # 기존 출처 패턴 폴백
    if not sources:
        fallback_patterns = [
            r'출처:\s*\[([^\]]+)\]\s*([^\n]+)',
            r'근거:\s*([^\n]+)',
        ]
        for pattern in fallback_patterns:
            for match in re.findall(pattern, content, re.IGNORECASE):
                text = ' '.join(match).strip() if isinstance(match, tuple) else match.strip()
                if text and len(text) > 10:
                    sources.append({"type": "text", "name": text[:100], "page": None})

    # 중복 제거
    seen = set()
    unique = []
    for s in sources:
        key = (s["name"], s.get("page"))
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:5]
```

**Step 2: render_evidence_preview 개선 — 구조화된 출처 표시**

```python
# components/chat_interface.py — render_evidence_preview 함수 교체
def render_evidence_preview(final_response):
    """근거 미리보기를 렌더링합니다."""
    preview_sources = extract_preview_sources(final_response)
    if preview_sources:
        with st.expander("📋 출처 정보", expanded=True):
            for i, source in enumerate(preview_sources, 1):
                if source["type"] == "pdf":
                    page_str = f" p.{source['page']}" if source.get("page") else ""
                    st.markdown(f"**{i}.** 📄 {source['name']}{page_str}")
                elif source["type"] == "web":
                    st.markdown(f"**{i}.** 🌐 [{source['name']}]({source['name']})")
                else:
                    st.markdown(f"**{i}.** {source['name']}")
```

**Step 3: import 정리**

`components/chat_interface.py`의 import에서 `extract_preview_sources`의 반환 타입 변경에 맞게 동작 확인. (타입만 변경, import 경로는 동일)

**Step 4: Commit**

```bash
git add utils/helpers.py components/chat_interface.py
git commit -m "feat: 출처 정보를 구조화하여 문서명/페이지/URL로 렌더링"
```

---

## Feature 2: 사용자 피드백 (좋아요/싫어요)

### Task 2.1: 피드백 저장소 모듈 생성

**Files:**
- Create: `core/feedback.py`

**Step 1: feedback 모듈 작성**

피드백을 JSON Lines 파일(`data/feedback.jsonl`)에 저장하는 간단한 모듈을 만든다.

```python
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
                total += 1
                record = json.loads(line)
                if record.get("rating") == 1:
                    positive += 1

    return {"total": total, "positive": positive, "negative": total - positive}
```

**Step 2: Commit**

```bash
git add core/feedback.py
git commit -m "feat: 사용자 피드백 JSONL 저장소 모듈 추가"
```

---

### Task 2.2: 채팅 인터페이스에 피드백 위젯 통합

**Files:**
- Modify: `app.py:620-636` (최종 응답 렌더링 부분)
- Modify: `core/state_manager.py` (피드백 키 상수 추가)

**Step 1: StateManager에 피드백 인덱스 관리 추가**

```python
# core/state_manager.py — 클래스 상수에 추가
FEEDBACK_INDEX = "feedback_index"

# initialize_session_state에 추가
if cls.FEEDBACK_INDEX not in st.session_state:
    st.session_state[cls.FEEDBACK_INDEX] = 0

# 새 메서드 추가
@classmethod
def get_feedback_index(cls) -> int:
    return st.session_state.get(cls.FEEDBACK_INDEX, 0)

@classmethod
def increment_feedback_index(cls):
    st.session_state[cls.FEEDBACK_INDEX] = cls.get_feedback_index() + 1
```

**Step 2: app.py 최종 응답 영역에 st.feedback 위젯 추가**

`app.py`의 최종 응답 표시 후(632줄 부근) 피드백 위젯을 추가한다.

```python
# app.py — final_response 표시 직후 (st.write(final_response) 다음)
st.write(final_response)
logger.info("[run] 최종 응답 길이=%d", len(final_response))

# 피드백 위젯
from core.feedback import save_feedback
feedback_key = f"feedback_{StateManager.get_feedback_index()}"
feedback_val = st.feedback("thumbs", key=feedback_key)
if feedback_val is not None:
    # st.feedback("thumbs")는 0(싫어요) 또는 1(좋아요) 반환
    last_query = ""
    for msg in reversed(StateManager.get_messages()):
        if msg["role"] == "user":
            last_query = msg["content"]
            break
    save_feedback(last_query, final_response, feedback_val)
    StateManager.increment_feedback_index()
    if feedback_val == 1:
        st.toast("감사합니다! 피드백이 저장되었습니다.", icon="👍")
    else:
        st.toast("피드백이 저장되었습니다. 개선에 참고하겠습니다.", icon="📝")

# 어시스턴트 메시지 추가
StateManager.add_message("assistant", final_response)
```

**Step 3: Commit**

```bash
git add app.py core/state_manager.py
git commit -m "feat: 채팅 응답에 좋아요/싫어요 피드백 위젯 추가"
```

---

### Task 2.3: 설정 페이지에 피드백 통계 표시

**Files:**
- Modify: `pages/01_⚙️_설정.py`

**Step 1: 설정 페이지에 피드백 통계 섹션 추가**

```python
# pages/01_⚙️_설정.py 하단에 추가
st.divider()
st.header("📊 피드백 통계")
from core.feedback import get_feedback_stats
stats = get_feedback_stats()
if stats["total"] > 0:
    col1, col2, col3 = st.columns(3)
    col1.metric("전체", stats["total"])
    col2.metric("👍 긍정", stats["positive"])
    col3.metric("👎 부정", stats["negative"])
    if stats["total"] > 0:
        ratio = stats["positive"] / stats["total"] * 100
        st.progress(ratio / 100, text=f"긍정률: {ratio:.0f}%")
else:
    st.info("아직 수집된 피드백이 없습니다.")
```

**Step 2: Commit**

```bash
git add pages/01_⚙️_설정.py
git commit -m "feat: 설정 페이지에 피드백 통계 대시보드 추가"
```

---

## Feature 3: 차트 생성 에이전트

### Task 3.1: plotly 의존성 추가 및 차트 생성 모듈

**Files:**
- Modify: `requirements.txt` (plotly 추가)
- Create: `core/chart_generator.py`

**Step 1: requirements.txt에 plotly 추가**

```
# requirements.txt 하단에 추가
plotly>=5.18.0
```

Run: `uv pip install plotly>=5.18.0`

**Step 2: chart_generator 모듈 작성**

```python
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
```

**Step 3: Commit**

```bash
git add requirements.txt core/chart_generator.py
git commit -m "feat: plotly 기반 차트 생성 모듈 추가"
```

---

### Task 3.2: LangGraph에 Chart Generator 에이전트 노드 추가

**Files:**
- Modify: `app.py:194-370` (`create_graph` 함수)

**Step 1: chart_agent 정의 및 graph에 노드 추가**

`create_graph` 함수 내에 chart_generator 에이전트를 추가한다. Analyst가 수치 데이터를 포함한 응답을 생성하면, 해당 응답에서 `chart_data` 블록을 추출하여 차트를 생성한다.

주의: chart_generator는 별도 LLM 에이전트가 아니라, Analyst 응답을 후처리하는 노드로 구현한다. 이렇게 하면 에이전트 간 라우팅 복잡성을 최소화할 수 있다.

```python
# app.py create_graph 함수 내 — analyst_agent 정의 후

# Analyst 시스템 프롬프트에 chart_data 지시 추가
analyst_system_prompt = """당신은 날카로운 통찰력을 가진 경제 분석가입니다. ...

**수치 데이터 시각화:**
분석에 시계열, 비교, 추이 등 수치 데이터가 포함되면 아래 형식으로 차트 데이터를 함께 출력하세요:

```chart_data
{
  "title": "차트 제목",
  "type": "line|bar|scatter",
  "x": ["label1", "label2", ...],
  "y": [value1, value2, ...],
  "x_label": "X축 레이블",
  "y_label": "Y축 레이블"
}
```

수치 데이터가 없거나 시각화가 불필요한 경우에는 chart_data 블록을 생략하세요.
"""

# chart_processor 노드 (Analyst → chart_processor → END)
from core.chart_generator import extract_chart_data, create_chart

def chart_processor_node(state):
    """Analyst 응답에서 chart_data를 추출하고 차트 생성 정보를 메시지에 추가한다."""
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}

    last_msg = messages[-1]
    content = getattr(last_msg, "content", "") or ""
    if isinstance(last_msg, dict):
        content = last_msg.get("content", "")

    chart_data = extract_chart_data(content)
    if chart_data:
        # chart_data를 세션 상태에 저장 (Streamlit에서 렌더링)
        import streamlit as st
        if "pending_charts" not in st.session_state:
            st.session_state["pending_charts"] = []
        fig = create_chart(chart_data)
        if fig:
            st.session_state["pending_charts"].append(fig)
            logger.info("[chart] 차트를 pending_charts에 추가")

    # 메시지를 그대로 전달 (chart_data 블록은 응답에 포함된 채로)
    return {"messages": []}

# graph 노드 교체: analyst → chart_processor → END
workflow.add_node("chart_processor", chart_processor_node)
workflow.add_edge("analyst", "chart_processor")
workflow.add_edge("chart_processor", END)
# 기존 workflow.add_edge("analyst", END) 삭제
```

**Step 2: app.py 응답 렌더링에서 pending_charts 표시**

```python
# app.py — render_evidence_preview 호출 직후
render_evidence_preview(final_response)

# 차트 렌더링
if "pending_charts" in st.session_state and st.session_state["pending_charts"]:
    for fig in st.session_state["pending_charts"]:
        st.plotly_chart(fig, use_container_width=True)
    st.session_state["pending_charts"] = []
```

**Step 3: Commit**

```bash
git add app.py core/chart_generator.py
git commit -m "feat: Analyst 응답의 수치 데이터를 자동 차트 변환하는 chart_processor 노드 추가"
```

---

### Task 3.3: Supervisor 라우팅 규칙에 chart 관련 안내 없음 확인

chart_processor는 Analyst 뒤에 자동으로 실행되므로 Supervisor 라우팅 변경이 불필요하다. 이 태스크는 검증만 수행한다.

**Step 1: create_supervisor 코드 확인 — 변경 불필요**

기존 Supervisor 라우팅(`ROUTE: researcher | analyst | END`)은 그대로 유지한다. chart_processor는 `analyst → chart_processor → END` 경로에서 자동 실행된다.

**Step 2: 수동 테스트**

"기준금리 추이를 분석해주세요" 같은 수치 데이터가 포함될 질문으로 테스트. Analyst가 chart_data 블록을 출력하면 차트가 렌더링되는지 확인.

**Step 3: Commit (테스트 결과 수정사항이 있을 경우만)**

---

## Feature 4: 공공 데이터 포털 연동 (KOSIS)

### Task 4.1: KOSIS API 클라이언트 모듈

**Files:**
- Create: `core/kosis_client.py`
- Modify: `core/config.py` (KOSIS API 키 설정 추가)

**Step 1: Config에 KOSIS 설정 추가**

```python
# core/config.py — 웹 검색 설정 섹션 아래에 추가
# ==============================================================================
# KOSIS (통계청) 설정
# ==============================================================================
KOSIS_API_KEY = os.getenv("KOSIS_API_KEY", "")
KOSIS_BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
```

**Step 2: kosis_client 모듈 작성**

```python
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
```

**Step 3: Commit**

```bash
git add core/kosis_client.py core/config.py
git commit -m "feat: KOSIS 통계청 API 클라이언트 모듈 추가"
```

---

### Task 4.2: Researcher 에이전트에 KOSIS 검색 도구 추가

**Files:**
- Modify: `app.py:196-218` (`create_graph` 내 researcher_tools)
- Modify: `app.py:220-260` (researcher_system_prompt)

**Step 1: researcher_tools에 KOSIS 도구 추가**

```python
# app.py create_graph 함수 — researcher_tools 정의 부분

# KOSIS 도구 추가 (API 키가 있을 경우만)
if Config.KOSIS_API_KEY:
    from core.kosis_client import search_kosis
    researcher_tools.append(
        Tool(
            name="kosis_statistics_search",
            func=search_kosis,
            description="KOSIS 국가통계포털에서 공식 통계 데이터를 검색합니다. 소비자물가지수, GDP, 실업률 등 한국 경제 통계를 조회할 때 사용하세요."
        )
    )
    logger.info("[graph] KOSIS 검색 도구 추가 완료")
```

**Step 2: researcher_system_prompt에 KOSIS 도구 안내 추가**

```python
# researcher_system_prompt 내 도구 목록에 추가
"""
- kosis_statistics_search: KOSIS 국가통계포털 공식 통계 데이터 검색 (API 키 필요)
"""

# 검색 전략에 추가
"""
**검색 전략:**
1. **1단계: 기본 검색** - bok_document_search와 web_search 사용
2. **1-1단계: 공식 통계** - 수치 데이터가 필요하면 kosis_statistics_search 사용
3. **2단계: 완화된 검색** - 기본 검색 실패 시 relaxed_document_search 사용
"""
```

**Step 3: env.example에 KOSIS_API_KEY 추가**

```
# env.example 하단에 추가
# KOSIS (통계청) 설정 (선택)
KOSIS_API_KEY=""
```

**Step 4: Commit**

```bash
git add app.py env.example
git commit -m "feat: Researcher 에이전트에 KOSIS 통계 검색 도구 추가"
```

---

### Task 4.3: 도움말 페이지에 KOSIS 사용법 안내 추가

**Files:**
- Modify: `pages/02_📖_도움말.py`

**Step 1: 도움말 페이지에 KOSIS 기능 설명 섹션 추가**

```python
# pages/02_📖_도움말.py — 기능 소개 섹션에 추가
st.subheader("📊 공공 데이터 연동 (KOSIS)")
st.markdown("""
- **KOSIS 국가통계포털**에서 공식 통계 데이터를 직접 검색합니다
- 소비자물가지수, GDP, 실업률, 수출입 통계 등 한국 경제 지표 조회 가능
- 사용하려면 `.env`에 `KOSIS_API_KEY`를 설정하세요
- API 키 발급: [KOSIS 오픈 API](https://kosis.kr/openapi/)에서 무료 발급
""")
```

**Step 2: Commit**

```bash
git add pages/02_📖_도움말.py
git commit -m "docs: 도움말 페이지에 KOSIS 공공 데이터 연동 안내 추가"
```

---

## 최종 검증 및 마무리

### Task 5.1: 전체 통합 테스트

**Step 1: 앱 실행 및 기능별 수동 테스트**

Run: `streamlit run app.py`

테스트 체크리스트:
- [ ] PDF 업로드 후 질문 → 응답에 문서명/페이지 번호 포함 확인
- [ ] 웹 검색 결과에 URL 출처 표시 확인
- [ ] 출처 정보 expander에 구조화된 출처 목록 표시 확인
- [ ] 각 응답에 좋아요/싫어요 버튼 표시 확인
- [ ] 피드백 저장 후 `data/feedback.jsonl`에 기록 확인
- [ ] 설정 페이지에서 피드백 통계 표시 확인
- [ ] 수치 데이터 포함 질문 시 차트 렌더링 확인 (Analyst가 chart_data 출력 시)
- [ ] KOSIS_API_KEY 없이 실행 시 KOSIS 도구 미등록 확인
- [ ] (KOSIS_API_KEY 설정 시) "소비자물가지수" 검색 후 통계 데이터 반환 확인

**Step 2: README.md 업데이트**

변경 이력 v2.3 섹션 추가:

```markdown
### v2.3 - Phase 2 기능 추가
- ✅ **답변 출처 명시**: PDF 문서명/페이지 번호, 웹 URL을 구조화하여 표시
- ✅ **사용자 피드백**: 좋아요/싫어요 위젯으로 응답 품질 수집
- ✅ **차트 생성**: Analyst 응답의 수치 데이터를 plotly 차트로 자동 시각화
- ✅ **KOSIS 연동**: 국가통계포털 API로 공식 경제 통계 조회 (선택)
```

**Step 3: Final Commit**

```bash
git add README.md
git commit -m "docs: v2.3 Phase 2 기능 추가 변경 이력 업데이트"
```

---

## 요약

| Feature | Tasks | 신규 파일 | 수정 파일 |
|---|---|---|---|
| 1. 출처 명시 | 1.1, 1.2, 1.3 | `core/citation.py` | `core/rag_pipeline.py`, `app.py`, `utils/helpers.py`, `components/chat_interface.py` |
| 2. 피드백 | 2.1, 2.2, 2.3 | `core/feedback.py` | `app.py`, `core/state_manager.py`, `pages/01_⚙️_설정.py` |
| 3. 차트 | 3.1, 3.2, 3.3 | `core/chart_generator.py` | `requirements.txt`, `app.py` |
| 4. KOSIS | 4.1, 4.2, 4.3 | `core/kosis_client.py` | `core/config.py`, `app.py`, `env.example`, `pages/02_📖_도움말.py` |
| 5. 마무리 | 5.1 | — | `README.md` |

**총 14개 Task, 4개 신규 파일, 10개 수정 파일**

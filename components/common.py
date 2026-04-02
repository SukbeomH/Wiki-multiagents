"""
공통 UI 컴포넌트 모듈
Streamlit 네이티브 컴포넌트 우선 사용으로 안정적이고 일관된 UI 제공
CSS 의존성 제거로 안정성 향상 및 유지보수성 개선
"""
import streamlit as st
from core.state_manager import StateManager


def render_header(title: str, description: str = ""):
    """헤더를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.header(title)
    if description:
        st.caption(description)


def render_footer():
    """푸터를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.divider()
    st.caption("AI 한국은행 경제 분석팀 - LangGraph 기반 협업형 멀티 에이전트 시스템")


def render_status_badge(status: str, color: str = "blue"):
    """상태 배지를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    if color == "green":
        st.success(status)
    elif color == "red":
        st.error(status)
    elif color == "yellow":
        st.warning(status)
    else:
        st.info(status)


def render_metric_card(title: str, value: str, description: str = ""):
    """메트릭 카드를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.subheader(title)
    st.metric(label="", value=value)
    if description:
        st.write(description)


def render_info_box(title: str, content: str):
    """정보 박스를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.info(f"**{title}**\n{content}")


def render_warning_box(title: str, content: str):
    """경고 박스를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.warning(f"**{title}**\n{content}")


def render_success_box(title: str, content: str):
    """성공 박스를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.success(f"**{title}**\n{content}")


def render_error_box(title: str, content: str):
    """오류 박스를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.error(f"**{title}**\n{content}")


def render_feature_card(title: str, description: str):
    """기능 카드를 렌더링합니다. (Streamlit 네이티브 컴포넌트 사용)"""
    st.subheader(title)
    st.write(description)


def render_pdf_page(filename: str, page: int = 1, height: int = 500):
    """PDF 파일의 특정 페이지를 iframe으로 렌더링한다."""
    import base64
    import os
    import streamlit.components.v1 as components
    from core.config import Config

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

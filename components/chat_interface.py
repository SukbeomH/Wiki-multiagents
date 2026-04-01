"""
채팅 인터페이스 컴포넌트 모듈
Streamlit 네이티브 컴포넌트 우선 사용으로 안정적이고 일관된 UI 제공
"""
import time
import streamlit as st
from core.logger import logger
from core.state_manager import StateManager
from utils.helpers import extract_preview_sources


def render_chat_messages():
    """채팅 메시지를 렌더링합니다."""
    messages = StateManager.get_messages()
    
    # 메시지 표시 영역을 컨테이너로 감싸기
    with st.container():
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # 분석 로그를 확장 가능한 형태로 표시 (로그 표시가 활성화된 경우에만)
        if StateManager.get_show_logs():
            recent_logs = logger.get_recent_logs(5)  # 최근 5개 로그 표시
            if recent_logs:
                with st.expander("📊 분석 로그 보기", expanded=False):
                    st.markdown("**실시간 분석 과정:**")
                    # 로그를 역순으로 표시 (최신 로그가 위에)
                    for log in reversed(recent_logs):
                        if "❌" in log or "🚨" in log:
                            st.error(log, icon="❌")
                        elif "⚠️" in log:
                            st.warning(log, icon="⚠️")
                        elif "ℹ️" in log:
                            st.info(log, icon="ℹ️")
                        else:
                            st.text(log)


# 주석 처리된 사용하지 않는 함수들 제거됨


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


def render_chat_interface():
    """전체 채팅 인터페이스를 렌더링합니다."""
    # # 고정 헤더 영역 (최상단)
    # with st.container():
    #     col1, col2 = st.columns([3, 1])
    #     with col1:
    #         st.header("🏦 AI 한국은행 경제 분석팀")
    #         st.caption("멀티 에이전트가 협력하여 질문에 대한 심층 분석을 제공합니다.")
    #     with col2:
    #         # 상태 정보 표시
    #         messages = StateManager.get_messages()
    #         message_count = len(messages) - 1  # 초기 메시지 제외
    #         web_search_status = "🌐 ON" if StateManager.get_web_search_enabled() else "🌐 OFF"
    #         st.info(f"💬 {message_count}개 메시지\n{web_search_status}")
    
    
    # 채팅 메시지 영역 (스크롤 가능)
    chat_container = st.container()
    with chat_container:
        render_chat_messages()
    
    # 채팅 입력창 (자연스러운 플로우)
    prompt = st.chat_input("기준금리, 경제 전망 등에 대해 질문하세요.", key="main_chat_input")
    
    return prompt
 
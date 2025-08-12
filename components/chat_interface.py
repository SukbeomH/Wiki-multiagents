"""
채팅 인터페이스 컴포넌트 모듈
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


def render_control_buttons():
    """컨트롤 버튼들을 렌더링합니다."""
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("🔄 초기화", help="현재 대화를 모두 지웁니다", type="secondary", use_container_width=True):
            StateManager.clear_messages()
            logger.clear_logs()
            st.rerun()
    
    with col2:
        web_search_enabled = st.toggle("🌐 웹검색", value=StateManager.get_web_search_enabled(), help="웹에서 최신 정보를 검색합니다")
        StateManager.set_web_search_enabled(web_search_enabled)
    
    with col3:
        # 로그 표시 토글
        log_button_text = "📊 로그 끄기" if StateManager.get_show_logs() else "📊 로그 켜기"
        log_button_type = "primary" if StateManager.get_show_logs() else "secondary"
        if st.button(log_button_text, help="실시간 분석 로그를 표시합니다", type=log_button_type, use_container_width=True):
            StateManager.toggle_show_logs()
            st.rerun()
    
    with col4:
        # 대화 내보내기 버튼
        if st.button("📥 내보내기", help="현재 대화를 파일로 내보냅니다", type="secondary", use_container_width=True):
            export_conversation()
    
    return web_search_enabled


def export_conversation():
    """대화를 파일로 내보냅니다."""
    messages = StateManager.get_messages()
    if len(messages) > 1:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"대화내역_{timestamp}.txt"
        
        export_content = f"AI 한국은행 경제 분석팀 - 대화 내역\n"
        export_content += f"생성일시: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_content += f"웹검색 활성화: {'예' if StateManager.get_web_search_enabled() else '아니오'}\n"
        export_content += "=" * 50 + "\n\n"
        
        for msg in messages:
            role = "사용자" if msg["role"] == "user" else "AI 분석팀"
            export_content += f"[{role}]\n{msg['content']}\n\n"
        
        st.download_button(
            label="📥 다운로드",
            data=export_content,
            file_name=filename,
            mime="text/plain",
            help="현재 대화를 텍스트 파일로 다운로드합니다"
        )
    else:
        st.warning("내보낼 대화가 없습니다.")


def render_chat_input():
    """채팅 입력 영역을 렌더링합니다."""
    prompt = st.chat_input("기준금리, 경제 전망 등에 대해 질문하세요.", key="main_chat_input")
    return prompt


def render_analysis_status():
    """분석 상태를 렌더링합니다."""
    # 실시간 로그 업데이트를 위한 컨테이너 (로그 표시가 활성화된 경우에만)
    if StateManager.get_show_logs():
        with st.container():
            recent_logs = logger.get_recent_logs(3)  # 최근 3개 로그만 표시
            if recent_logs:
                st.markdown("**📊 실시간 분석 로그:**")
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


def render_evidence_preview(final_response):
    """근거 미리보기를 렌더링합니다."""
    preview_sources = extract_preview_sources(final_response)
    if preview_sources:
        with st.expander("📋 근거 미리보기", expanded=False):
            st.markdown("**주요 근거 정보:**")
            for i, source in enumerate(preview_sources[:3], 1):
                st.markdown(f"**{i}.** {source}")


def render_chat_interface():
    """전체 채팅 인터페이스를 렌더링합니다."""
    # 메인 컨테이너
    with st.container():
        st.title("🏦 AI 한국은행 경제 분석팀 (LangGraph v0.3.x)")
        st.markdown("멀티 에이전트가 협력하여 질문에 대한 심층 분석을 제공합니다.")
        
        # 채팅 메시지 영역
        render_chat_messages()
        
        # 컨트롤 버튼 영역
        web_search_enabled = render_control_buttons()
        
        # 채팅 입력 영역
        prompt = render_chat_input()
        
        return prompt, web_search_enabled 
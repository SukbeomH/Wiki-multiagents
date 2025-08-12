"""
공통 UI 컴포넌트 모듈
여러 페이지에서 재사용할 수 있는 컴포넌트들을 정의합니다.
"""
import streamlit as st
from core import Config
from core.state_manager import StateManager


def render_header():
    """앱 헤더를 렌더링합니다."""
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1>🏦 AI 한국은행 경제 분석팀</h1>
        <p style="color: #666; font-size: 1.1rem;">
            한국은행 공식 문서 기반 경제 분석 AI 시스템
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """앱 푸터를 렌더링합니다."""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>© 2024 AI 한국은행 경제 분석팀 | 한국은행 공식 문서 기반 분석</p>
        <p>정확하고 신뢰할 수 있는 경제 분석을 제공합니다.</p>
    </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: str, text: str):
    """상태 배지를 렌더링합니다."""
    color_map = {
        "success": "🟢",
        "warning": "🟡", 
        "error": "🔴",
        "info": "🔵"
    }
    
    emoji = color_map.get(status, "⚪")
    st.markdown(f"{emoji} **{text}**")


def render_metric_card(title: str, value: str, description: str = ""):
    """메트릭 카드를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            background-color: #f8f9fa;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #333;">{title}</h4>
            <p style="margin: 0; font-size: 1.5rem; font-weight: bold; color: #0066cc;">{value}</p>
            {f'<p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.9rem;">{description}</p>' if description else ''}
        </div>
        """, unsafe_allow_html=True)


def render_info_box(title: str, content: str, icon: str = "ℹ️"):
    """정보 박스를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border-left: 4px solid #0066cc;
            background-color: #f0f8ff;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #0066cc;">{icon} {title}</h4>
            <p style="margin: 0; color: #333;">{content}</p>
        </div>
        """, unsafe_allow_html=True)


def render_warning_box(title: str, content: str, icon: str = "⚠️"):
    """경고 박스를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border-left: 4px solid #ff9900;
            background-color: #fff8f0;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #ff9900;">{icon} {title}</h4>
            <p style="margin: 0; color: #333;">{content}</p>
        </div>
        """, unsafe_allow_html=True)


def render_success_box(title: str, content: str, icon: str = "✅"):
    """성공 박스를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border-left: 4px solid #00cc66;
            background-color: #f0fff8;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #00cc66;">{icon} {title}</h4>
            <p style="margin: 0; color: #333;">{content}</p>
        </div>
        """, unsafe_allow_html=True)


def render_error_box(title: str, content: str, icon: str = "❌"):
    """오류 박스를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border-left: 4px solid #cc0000;
            background-color: #fff0f0;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        ">
            <h4 style="margin: 0 0 0.5rem 0; color: #cc0000;">{icon} {title}</h4>
            <p style="margin: 0; color: #333;">{content}</p>
        </div>
        """, unsafe_allow_html=True)


def render_feature_card(title: str, description: str, icon: str = "🔧"):
    """기능 카드를 렌더링합니다."""
    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <span style="font-size: 2rem; margin-right: 1rem;">{icon}</span>
                <h3 style="margin: 0; color: #333;">{title}</h3>
            </div>
            <p style="margin: 0; color: #666; line-height: 1.6;">{description}</p>
        </div>
        """, unsafe_allow_html=True)


def render_navigation_buttons():
    """네비게이션 버튼들을 렌더링합니다."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 메인", use_container_width=True):
            st.switch_page("app_refactored.py")
    
    with col2:
        if st.button("⚙️ 설정", use_container_width=True):
            st.switch_page("pages/01_⚙️_설정.py")
    
    with col3:
        if st.button("📖 도움말", use_container_width=True):
            st.switch_page("pages/02_📖_도움말.py")


def render_page_info(title: str, description: str, icon: str = "📄"):
    """페이지 정보를 렌더링합니다."""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h1 style="margin: 0 0 0.5rem 0; font-size: 2.5rem;">{icon}</h1>
        <h2 style="margin: 0 0 1rem 0;">{title}</h2>
        <p style="margin: 0; font-size: 1.1rem; opacity: 0.9;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_loading_spinner(text: str = "로딩 중..."):
    """로딩 스피너를 렌더링합니다."""
    with st.spinner(text):
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem;">
            <div style="
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #0066cc;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            "></div>
            <p style="margin-top: 1rem; color: #666;">{text}</p>
        </div>
        <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        """, unsafe_allow_html=True)


def render_progress_bar(current: int, total: int, label: str = "진행률"):
    """진행률 바를 렌더링합니다."""
    progress = current / total if total > 0 else 0
    st.progress(progress, text=f"{label}: {current}/{total} ({progress:.1%})")


def render_session_summary():
    """세션 요약 정보를 렌더링합니다."""
    session_info = StateManager.get_session_info()
    
    st.subheader("📊 현재 세션 정보")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_metric_card(
            "메시지 수",
            str(session_info["messages_count"]),
            "현재 대화의 메시지 수"
        )
    
    with col2:
        render_metric_card(
            "웹검색",
            "활성화" if session_info["web_search_enabled"] else "비활성화",
            "웹 검색 기능 상태"
        )
    
    with col3:
        render_metric_card(
            "그래프 상태",
            "유효" if session_info["agent_graph_valid"] else "무효",
            "AI 에이전트 그래프 상태"
        )


def render_config_summary():
    """설정 요약 정보를 렌더링합니다."""
    settings = Config.get_all_settings()
    
    st.subheader("🔧 주요 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_metric_card("Azure API 버전", settings["azure_api_version"])
        render_metric_card("로그 레벨", settings["log_level"])
        render_metric_card("RAG 전략", settings["rag_search_strategy"])
    
    with col2:
        render_metric_card("데이터 디렉토리", settings["data_dir"])
        render_metric_card("최대 반복", str(settings["max_iterations"]))
        render_metric_card("타임아웃", f"{settings['timeout_seconds']}초")


def render_help_tooltip(text: str, help_text: str):
    """도움말 툴팁을 렌더링합니다."""
    st.markdown(f"""
    <div style="position: relative; display: inline-block;">
        <span style="
            cursor: help;
            color: #0066cc;
            text-decoration: underline;
        " title="{help_text}">{text}</span>
    </div>
    """, unsafe_allow_html=True) 
"""
중앙화된 상태 관리 모듈
"""
import streamlit as st
from typing import Dict, Any, List, Optional
from core.config import Config
from core.logger import logger


class StateManager:
    """Streamlit 세션 상태를 중앙에서 관리하는 클래스"""
    
    # 상태 키 상수
    UPLOADER_KEY = "uploader_key"
    AGENT_GRAPH = "agent_graph"
    AGENT_GRAPH_VERSION = "agent_graph_version"
    MESSAGES = "messages"
    WEB_SEARCH_ENABLED = "web_search_enabled"
    SHOW_LOGS = "show_logs"
    FEEDBACK_INDEX = "feedback_index"
    
    @classmethod
    def initialize_session_state(cls):
        """세션 상태를 초기화합니다."""
        if cls.UPLOADER_KEY not in st.session_state:
            st.session_state[cls.UPLOADER_KEY] = 0
        
        if cls.WEB_SEARCH_ENABLED not in st.session_state:
            st.session_state[cls.WEB_SEARCH_ENABLED] = True
        
        if cls.SHOW_LOGS not in st.session_state:
            st.session_state[cls.SHOW_LOGS] = False
        
        if cls.MESSAGES not in st.session_state:
            st.session_state[cls.MESSAGES] = [
                {
                    "role": "assistant",
                    "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"
                }
            ]

        if cls.FEEDBACK_INDEX not in st.session_state:
            st.session_state[cls.FEEDBACK_INDEX] = 0

        logger.info("[state] 세션 상태 초기화 완료")
    
    @classmethod
    def get_messages(cls) -> List[Dict[str, str]]:
        """메시지 목록을 반환합니다."""
        return st.session_state.get(cls.MESSAGES, [])
    
    @classmethod
    def add_message(cls, role: str, content: str):
        """메시지를 추가합니다."""
        if cls.MESSAGES not in st.session_state:
            st.session_state[cls.MESSAGES] = []
        
        st.session_state[cls.MESSAGES].append({
            "role": role,
            "content": content
        })
        logger.info("[state] 메시지 추가: %s (%d자)", role, len(content))
    
    @classmethod
    def clear_messages(cls):
        """메시지를 초기화합니다."""
        st.session_state[cls.MESSAGES] = [
            {
                "role": "assistant", 
                "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"
            }
        ]
        logger.info("[state] 메시지 초기화 완료")
    
    @classmethod
    def get_agent_graph(cls):
        """에이전트 그래프를 반환합니다."""
        return st.session_state.get(cls.AGENT_GRAPH)
    
    @classmethod
    def set_agent_graph(cls, graph, version: str = None):
        """에이전트 그래프를 설정합니다."""
        st.session_state[cls.AGENT_GRAPH] = graph
        if version:
            st.session_state[cls.AGENT_GRAPH_VERSION] = version
        logger.info("[state] 에이전트 그래프 설정: version=%s", version)
    
    @classmethod
    def is_agent_graph_valid(cls) -> bool:
        """에이전트 그래프가 유효한지 확인합니다."""
        return (
            cls.AGENT_GRAPH in st.session_state and 
            st.session_state.get(cls.AGENT_GRAPH_VERSION) == Config.APP_GRAPH_VERSION
        )
    
    @classmethod
    def clear_agent_graph(cls):
        """에이전트 그래프를 초기화합니다."""
        st.session_state.pop(cls.AGENT_GRAPH, None)
        st.session_state.pop(cls.AGENT_GRAPH_VERSION, None)
        logger.info("[state] 에이전트 그래프 초기화 완료")
    
    @classmethod
    def get_uploader_key(cls) -> int:
        """업로더 키를 반환합니다."""
        return st.session_state.get(cls.UPLOADER_KEY, 0)
    
    @classmethod
    def increment_uploader_key(cls):
        """업로더 키를 증가시킵니다."""
        current_key = st.session_state.get(cls.UPLOADER_KEY, 0)
        st.session_state[cls.UPLOADER_KEY] = current_key + 1
        logger.info("[state] 업로더 키 증가: %d -> %d", current_key, current_key + 1)
    
    @classmethod
    def get_web_search_enabled(cls) -> bool:
        """웹검색 활성화 상태를 반환합니다."""
        return st.session_state.get(cls.WEB_SEARCH_ENABLED, True)
    
    @classmethod
    def set_web_search_enabled(cls, enabled: bool):
        """웹검색 활성화 상태를 설정합니다."""
        st.session_state[cls.WEB_SEARCH_ENABLED] = enabled
        logger.info("[state] 웹검색 상태 변경: %s", enabled)
    
    @classmethod
    def get_show_logs(cls) -> bool:
        """로그 표시 상태를 반환합니다."""
        return st.session_state.get(cls.SHOW_LOGS, False)
    
    @classmethod
    def set_show_logs(cls, show: bool):
        """로그 표시 상태를 설정합니다."""
        st.session_state[cls.SHOW_LOGS] = show
        logger.info("[state] 로그 표시 상태 변경: %s", show)
    
    @classmethod
    def toggle_show_logs(cls):
        """로그 표시 상태를 토글합니다."""
        current = cls.get_show_logs()
        cls.set_show_logs(not current)
    
    @classmethod
    def get_feedback_index(cls) -> int:
        """피드백 위젯 키 인덱스를 반환합니다."""
        return st.session_state.get(cls.FEEDBACK_INDEX, 0)

    @classmethod
    def increment_feedback_index(cls):
        """피드백 위젯 키 인덱스를 증가시킵니다."""
        st.session_state[cls.FEEDBACK_INDEX] = cls.get_feedback_index() + 1

    @classmethod
    def get_session_info(cls) -> Dict[str, Any]:
        """세션 정보를 반환합니다."""
        return {
            "uploader_key": cls.get_uploader_key(),
            "messages_count": len(cls.get_messages()),
            "web_search_enabled": cls.get_web_search_enabled(),
            "show_logs": cls.get_show_logs(),
            "agent_graph_valid": cls.is_agent_graph_valid(),
            "agent_graph_version": st.session_state.get(cls.AGENT_GRAPH_VERSION)
        }
    
    @classmethod
    def reset_all(cls):
        """모든 상태를 초기화합니다."""
        st.session_state.clear()
        cls.initialize_session_state()
        logger.info("[state] 모든 상태 초기화 완료") 
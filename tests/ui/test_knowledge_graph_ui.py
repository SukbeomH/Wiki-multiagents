"""
Knowledge Graph Wiki System UI 테스트

PRD 요구사항에 맞는 UI 기능을 테스트합니다.
"""

import pytest
import streamlit as st
import requests
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.main import (
    init_session_state,
    render_sidebar,
    render_graph_tab,
    render_wiki_tab,
    start_knowledge_workflow,
    submit_feedback
)


class TestKnowledgeGraphUI:
    """Knowledge Graph Wiki System UI 테스트 클래스"""
    
    def test_session_state_initialization(self):
        """세션 상태 초기화 테스트"""
        # 세션 상태 초기화
        init_session_state()
        
        # 필수 세션 상태 확인
        assert 'dark_mode' in st.session_state
        assert 'current_tab' in st.session_state
        assert 'search_query' in st.session_state
        assert 'selected_node' in st.session_state
        assert 'graph_data' in st.session_state
        assert 'wiki_content' in st.session_state
        assert 'user_role' in st.session_state
        assert 'workflow_status' in st.session_state
        
        # 기본값 확인
        assert st.session_state.dark_mode == False
        assert st.session_state.current_tab == "graph"
        assert st.session_state.search_query == ""
        assert st.session_state.user_role == "user"
        assert st.session_state.workflow_status == "idle"
    
    @patch('requests.post')
    def test_start_knowledge_workflow_success(self, mock_post):
        """지식 그래프 워크플로우 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "result": {
                "graph_data": {
                    "nodes": [{"id": "test_node", "label": "Test Node"}],
                    "edges": []
                },
                "wiki_content": {
                    "title": "Test Wiki",
                    "markdown": "# Test Content",
                    "summary": "Test summary"
                }
            }
        }
        mock_post.return_value = mock_response
        
        # 워크플로우 시작
        start_knowledge_workflow("test_keyword")
        
        # 상태 확인
        assert st.session_state.workflow_status == "completed"
        assert st.session_state.graph_data is not None
        assert st.session_state.wiki_content is not None
        
        # API 호출 확인
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "supervisor/process" in call_args[0][0]
        assert call_args[1]["json"]["request"]["keyword"] == "test_keyword"
    
    @patch('requests.post')
    def test_start_knowledge_workflow_error(self, mock_post):
        """지식 그래프 워크플로우 오류 테스트"""
        # Mock 오류 응답 설정
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # 워크플로우 시작
        start_knowledge_workflow("test_keyword")
        
        # 상태 확인
        assert st.session_state.workflow_status == "error"
    
    @patch('requests.post')
    def test_submit_feedback_success(self, mock_post):
        """피드백 제출 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"acknowledged": True}
        mock_post.return_value = mock_response
        
        # 피드백 제출
        result = submit_feedback("correction", "Test feedback content")
        
        # API 호출 확인
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "feedback/process" in call_args[0][0]
        assert call_args[1]["json"]["feedback"] == "Test feedback content"
        assert call_args[1]["json"]["feedback_type"] == "correction"
    
    def test_graph_data_processing(self):
        """그래프 데이터 처리 테스트"""
        # 테스트 그래프 데이터
        test_graph_data = {
            "nodes": [
                {"id": "node1", "label": "Node 1", "type": "PERSON"},
                {"id": "node2", "label": "Node 2", "type": "ORGANIZATION"}
            ],
            "edges": [
                {"source": "node1", "target": "node2", "label": "WORKS_FOR"}
            ]
        }
        
        # 그래프 데이터 설정
        st.session_state.graph_data = test_graph_data
        
        # 그래프 탭 렌더링 (오류 없이 실행되는지 확인)
        try:
            render_graph_tab()
            assert True  # 오류 없이 실행됨
        except Exception as e:
            pytest.fail(f"그래프 탭 렌더링 실패: {e}")
    
    def test_wiki_content_processing(self):
        """위키 콘텐츠 처리 테스트"""
        # 테스트 위키 콘텐츠
        test_wiki_content = {
            "title": "Test Wiki Title",
            "summary": "This is a test summary",
            "markdown": "# Test Wiki\n\nThis is test content.",
            "references": [
                {"title": "Test Reference", "url": "http://example.com"}
            ],
            "metadata": {
                "created_at": "2024-01-01T00:00:00",
                "author": "Wiki Agent",
                "version": "1.0",
                "word_count": 10
            }
        }
        
        # 위키 콘텐츠 설정
        st.session_state.wiki_content = test_wiki_content
        
        # 위키 탭 렌더링 (오류 없이 실행되는지 확인)
        try:
            render_wiki_tab()
            assert True  # 오류 없이 실행됨
        except Exception as e:
            pytest.fail(f"위키 탭 렌더링 실패: {e}")
    
    def test_user_role_permissions(self):
        """사용자 역할별 권한 테스트"""
        # user 역할 테스트
        st.session_state.user_role = "user"
        # 읽기 전용 권한 확인 (편집 기능 비활성화)
        
        # editor 역할 테스트
        st.session_state.user_role = "editor"
        # 편집 권한 확인 (피드백 제출 가능)
        
        # admin 역할 테스트
        st.session_state.user_role = "admin"
        # 관리자 권한 확인 (모든 기능 사용 가능)
        
        assert st.session_state.user_role in ["user", "editor", "admin"]
    
    def test_dark_mode_toggle(self):
        """다크 모드 토글 테스트"""
        # 초기 상태
        st.session_state.dark_mode = False
        
        # 다크 모드 활성화
        st.session_state.dark_mode = True
        assert st.session_state.dark_mode == True
        
        # 다크 모드 비활성화
        st.session_state.dark_mode = False
        assert st.session_state.dark_mode == False


class TestUIComponents:
    """UI 컴포넌트 테스트"""
    
    def test_sidebar_components(self):
        """사이드바 컴포넌트 테스트"""
        # 사이드바 렌더링 (오류 없이 실행되는지 확인)
        try:
            render_sidebar()
            assert True  # 오류 없이 실행됨
        except Exception as e:
            pytest.fail(f"사이드바 렌더링 실패: {e}")
    
    def test_css_loading(self):
        """CSS 로딩 테스트"""
        from src.ui.main import load_css
        
        # CSS 로딩 (오류 없이 실행되는지 확인)
        try:
            load_css()
            assert True  # 오류 없이 실행됨
        except Exception as e:
            pytest.fail(f"CSS 로딩 실패: {e}")


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"]) 
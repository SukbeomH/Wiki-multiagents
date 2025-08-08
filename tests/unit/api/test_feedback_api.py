"""
Feedback API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.api.main import app
from src.agents.feedback import FeedbackAgent, FeedbackItem

client = TestClient(app)


class TestFeedbackAPI:
    """Feedback API 테스트 클래스"""
    
    @pytest.fixture
    def mock_feedback_agent(self):
        """Mock Feedback Agent"""
        with patch('src.api.routes.feedback.feedback_agent') as mock:
            # 기본 Mock 설정
            mock.get_feedback.return_value = None
            mock.list_feedback.return_value = []
            mock.update_feedback_status.return_value = False
            mock.get_feedback_statistics.return_value = {}
            mock.health_check.return_value = {}
            yield mock
    
    def test_submit_feedback_success(self, mock_feedback_agent):
        """피드백 제출 성공 테스트"""
        # Mock 설정
        mock_result = {
            "acknowledged": True,
            "feedback_id": "test_workflow",  # node_id가 feedback_id가 됨
            "processing_status": "processed",
            "estimated_impact": {"priority": "medium", "affected_components": ["workflow"]},
            "requires_human_review": False
        }
        mock_feedback_agent.process.return_value = mock_result
        
        # 요청 데이터
        request_data = {
            "workflow_id": "test_workflow",
            "user_id": "test_user",
            "feedback_type": "bug_report",
            "content": "테스트 버그 리포트",
            "rating": 3
        }
        
        # API 호출
        response = client.post("/api/v1/feedback/submit", json=request_data)
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] is True
        assert result["feedback_id"] == "test_workflow"
        assert result["processing_status"] == "processed"
        
        # Mock 호출 검증
        mock_feedback_agent.process.assert_called_once()
    
    def test_submit_feedback_failure(self, mock_feedback_agent):
        """피드백 제출 실패 테스트"""
        # Mock 설정 - 예외 발생
        mock_feedback_agent.process.side_effect = Exception("Database error")
        
        # 요청 데이터
        request_data = {
            "workflow_id": "test_workflow",
            "user_id": "test_user",
            "feedback_type": "bug_report",
            "content": "테스트 버그 리포트"
        }
        
        # API 호출
        response = client.post("/api/v1/feedback/submit", json=request_data)
        
        # 검증
        assert response.status_code == 500
        assert "피드백 제출 실패" in response.json()["detail"]
    
    def test_get_feedback_success(self, mock_feedback_agent):
        """피드백 조회 성공 테스트"""
        # Mock 설정
        mock_feedback = FeedbackItem(
            id="test_feedback_1",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="bug_report",
            content="테스트 버그 리포트",
            rating=3,
            status="processed",
            created_at=datetime.now(),
            processed_at=datetime.now()
        )
        mock_feedback_agent.get_feedback.return_value = mock_feedback
        
        # API 호출
        response = client.get("/api/v1/feedback/test_feedback_1")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["feedback_id"] == "test_feedback_1"
        assert result["content"] == "테스트 버그 리포트"
        assert result["rating"] == 3
        
        # Mock 호출 검증
        mock_feedback_agent.get_feedback.assert_called_once_with("test_feedback_1")
    
    def test_get_feedback_not_found(self, mock_feedback_agent):
        """피드백 조회 - 찾을 수 없음 테스트"""
        # Mock 설정 - None 반환
        mock_feedback_agent.get_feedback.return_value = None
        
        # API 호출
        response = client.get("/api/v1/feedback/nonexistent")
        
        # 검증
        assert response.status_code == 404
        assert "피드백을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_list_feedback_success(self, mock_feedback_agent):
        """피드백 목록 조회 성공 테스트"""
        # Mock 설정
        mock_feedbacks = [
            FeedbackItem(
                id="test_feedback_1",
                workflow_id="test_workflow",
                user_id="test_user",
                feedback_type="bug_report",
                content="테스트 버그 리포트 1",
                rating=3,
                status="processed",
                created_at=datetime.now(),
                processed_at=datetime.now()
            ),
            FeedbackItem(
                id="test_feedback_2",
                workflow_id="test_workflow",
                user_id="test_user",
                feedback_type="feature_request",
                content="테스트 기능 요청",
                rating=5,
                status="pending",
                created_at=datetime.now(),
                processed_at=None
            )
        ]
        mock_feedback_agent.list_feedback.return_value = mock_feedbacks
        
        # API 호출
        response = client.get("/api/v1/feedback/")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 2
        assert len(result["feedbacks"]) == 2
        assert result["feedbacks"][0]["feedback_id"] == "test_feedback_1"
        assert result["feedbacks"][1]["feedback_id"] == "test_feedback_2"
        
        # Mock 호출 검증
        mock_feedback_agent.list_feedback.assert_called_once_with(
            workflow_id=None, user_id=None, status=None, limit=100
        )
    
    def test_list_feedback_with_filters(self, mock_feedback_agent):
        """피드백 목록 조회 - 필터 적용 테스트"""
        # Mock 설정
        mock_feedbacks = [
            FeedbackItem(
                id="test_feedback_1",
                workflow_id="test_workflow",
                user_id="test_user",
                feedback_type="bug_report",
                content="테스트 버그 리포트",
                rating=3,
                status="processed",
                created_at=datetime.now(),
                processed_at=datetime.now()
            )
        ]
        mock_feedback_agent.list_feedback.return_value = mock_feedbacks
        
        # API 호출 - 필터 적용
        response = client.get("/api/v1/feedback/?workflow_id=test_workflow&status=processed&limit=50")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 1
        
        # Mock 호출 검증 - 필터 파라미터 확인
        mock_feedback_agent.list_feedback.assert_called_once_with(
            workflow_id="test_workflow", user_id=None, status="processed", limit=50
        )
    
    def test_update_feedback_status_success(self, mock_feedback_agent):
        """피드백 상태 업데이트 성공 테스트"""
        # Mock 설정
        mock_feedback_agent.update_feedback_status.return_value = True
        
        # API 호출
        response = client.put("/api/v1/feedback/test_feedback_1/status?status=processed")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert "업데이트되었습니다" in result["message"]
        
        # Mock 호출 검증
        mock_feedback_agent.update_feedback_status.assert_called_once_with("test_feedback_1", "processed")
    
    def test_update_feedback_status_not_found(self, mock_feedback_agent):
        """피드백 상태 업데이트 - 찾을 수 없음 테스트"""
        # Mock 설정 - False 반환
        mock_feedback_agent.update_feedback_status.return_value = False
        
        # API 호출
        response = client.put("/api/v1/feedback/nonexistent/status?status=processed")
        
        # 검증
        assert response.status_code == 404
        assert "피드백을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_get_feedback_statistics_success(self, mock_feedback_agent):
        """피드백 통계 조회 성공 테스트"""
        # Mock 설정 - 실제 반환값과 일치하도록 수정
        mock_stats = {
            "total_feedback": 10,
            "status_counts": {"pending": 5, "processed": 5},
            "rating_counts": {"3": 3, "4": 4, "5": 3},
            "recent_feedback": 2,
            "generated_at": "2025-08-08T16:30:00"
        }
        # Mock 설정을 명시적으로 재설정
        mock_feedback_agent.get_feedback_statistics.return_value = mock_stats
        
        # API 호출
        response = client.get("/api/v1/feedback/statistics")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["total_feedback"] == 10
        assert result["status_counts"]["pending"] == 5
        assert result["rating_counts"]["3"] == 3
        assert result["recent_feedback"] == 2
        
        # Mock 호출 검증
        mock_feedback_agent.get_feedback_statistics.assert_called_once()
    
    def test_health_check_success(self, mock_feedback_agent):
        """상태 확인 성공 테스트"""
        # Mock 설정 - 실제 반환값과 일치하도록 수정
        mock_health = {
            "status": "healthy",
            "agent_type": "feedback",
            "timestamp": "2025-08-08T16:30:00",
            "config": {
                "database_path": "data/feedback.db",
                "total_feedback": 5
            },
            "statistics": {
                "total_feedback": 5,
                "status_counts": {"pending": 2, "processed": 3},
                "rating_counts": {},
                "recent_feedback": 1,
                "generated_at": "2025-08-08T16:30:00"
            }
        }
        # Mock 설정을 명시적으로 재설정
        mock_feedback_agent.health_check.return_value = mock_health
        
        # API 호출
        response = client.get("/api/v1/feedback/health")
        
        # 검증
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "healthy"
        assert result["agent_type"] == "feedback"
        
        # Mock 호출 검증
        mock_feedback_agent.health_check.assert_called_once()
    
    def test_health_check_failure(self, mock_feedback_agent):
        """상태 확인 실패 테스트"""
        # Mock 설정 - 예외 발생
        mock_feedback_agent.health_check.side_effect = Exception("Database connection failed")
        
        # API 호출
        response = client.get("/api/v1/feedback/health")
        
        # 검증
        assert response.status_code == 500
        assert "상태 확인 실패" in response.json()["detail"]
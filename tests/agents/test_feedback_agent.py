"""
Feedback Agent 테스트
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.agents.feedback import FeedbackAgent, FeedbackItem


class TestFeedbackAgent:
    """Feedback Agent 테스트 클래스"""
    
    @pytest.fixture
    def feedback_agent(self, tmp_path):
        """테스트용 Feedback Agent 인스턴스"""
        db_path = tmp_path / "feedback.db"
        return FeedbackAgent(str(db_path))
    
    def test_feedback_agent_initialization(self, feedback_agent):
        """Feedback Agent 초기화 테스트"""
        assert feedback_agent is not None
        assert hasattr(feedback_agent, 'db_path')
        assert hasattr(feedback_agent, 'slack_webhook_url')
        assert feedback_agent.db_path.exists()
    
    def test_submit_feedback(self, feedback_agent):
        """피드백 제출 테스트"""
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_1",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="bug_report",
            content="테스트 버그 리포트",
            rating=3
        )
        
        result = feedback_agent.submit_feedback(feedback_item)
        assert result is True
    
    def test_get_feedback(self, feedback_agent):
        """피드백 조회 테스트"""
        # 피드백 제출
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_2",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="feature_request",
            content="새로운 기능 요청",
            rating=5
        )
        feedback_agent.submit_feedback(feedback_item)
        
        # 피드백 조회
        retrieved_feedback = feedback_agent.get_feedback("test_feedback_2")
        
        assert retrieved_feedback is not None
        assert retrieved_feedback.feedback_id == "test_feedback_2"
        assert retrieved_feedback.content == "새로운 기능 요청"
        assert retrieved_feedback.rating == 5
        assert retrieved_feedback.status == "pending"
    
    def test_list_feedback(self, feedback_agent):
        """피드백 목록 조회 테스트"""
        # 여러 피드백 제출
        feedback_items = [
            FeedbackItem(
                feedback_id=f"test_feedback_{i}",
                workflow_id="test_workflow",
                user_id="test_user",
                feedback_type="general",
                content=f"테스트 피드백 {i}",
                rating=i
            )
            for i in range(1, 4)
        ]
        
        for item in feedback_items:
            feedback_agent.submit_feedback(item)
        
        # 전체 목록 조회
        all_feedback = feedback_agent.list_feedback()
        assert len(all_feedback) == 3
        
        # 워크플로우별 필터링
        workflow_feedback = feedback_agent.list_feedback(workflow_id="test_workflow")
        assert len(workflow_feedback) == 3
        
        # 존재하지 않는 워크플로우
        empty_feedback = feedback_agent.list_feedback(workflow_id="nonexistent")
        assert len(empty_feedback) == 0
    
    def test_update_feedback_status(self, feedback_agent):
        """피드백 상태 업데이트 테스트"""
        # 피드백 제출
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_3",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="bug_report",
            content="버그 리포트"
        )
        feedback_agent.submit_feedback(feedback_item)
        
        # 상태 업데이트
        result = feedback_agent.update_feedback_status("test_feedback_3", "processed")
        assert result is True
        
        # 업데이트된 상태 확인
        updated_feedback = feedback_agent.get_feedback("test_feedback_3")
        assert updated_feedback.status == "processed"
        assert updated_feedback.processed_at is not None
    
    @pytest.mark.asyncio
    async def test_send_slack_notification(self, feedback_agent):
        """Slack 알림 전송 테스트"""
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_4",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="bug_report",
            content="중요한 버그 발견"
        )
        
        # Slack webhook URL이 없는 경우
        result = await feedback_agent.send_slack_notification(feedback_item)
        assert result is False
        
        # Slack webhook URL이 있는 경우
        feedback_agent.slack_webhook_url = "https://hooks.slack.com/test"
        result = await feedback_agent.send_slack_notification(feedback_item)
        assert result is True
    
    def test_process_feedback(self, feedback_agent):
        """피드백 처리 테스트"""
        # 버그 리포트 제출
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_5",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="bug_report",
            content="Critical bug found"
        )
        feedback_agent.submit_feedback(feedback_item)
        
        # 피드백 처리
        result = feedback_agent.process_feedback("test_feedback_5")
        
        assert result["success"] is True
        assert result["action"] == "bug_report_processed"
        assert result["priority"] == "high"
        
        # 처리된 상태 확인
        processed_feedback = feedback_agent.get_feedback("test_feedback_5")
        assert processed_feedback.status == "processed"
    
    def test_process_feature_request(self, feedback_agent):
        """기능 요청 처리 테스트"""
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_6",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="feature_request",
            content="새로운 기능 요청"
        )
        feedback_agent.submit_feedback(feedback_item)
        
        result = feedback_agent.process_feedback("test_feedback_6")
        
        assert result["success"] is True
        assert result["action"] == "feature_request_processed"
        assert result["priority"] == "medium"
    
    def test_process_general_feedback(self, feedback_agent):
        """일반 피드백 처리 테스트"""
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_7",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="general",
            content="일반적인 피드백"
        )
        feedback_agent.submit_feedback(feedback_item)
        
        result = feedback_agent.process_feedback("test_feedback_7")
        
        assert result["success"] is True
        assert result["action"] == "general_feedback_processed"
        assert result["priority"] == "low"
    
    def test_process_unknown_feedback_type(self, feedback_agent):
        """알 수 없는 피드백 타입 처리 테스트"""
        feedback_item = FeedbackItem(
            feedback_id="test_feedback_8",
            workflow_id="test_workflow",
            user_id="test_user",
            feedback_type="unknown_type",
            content="알 수 없는 타입"
        )
        feedback_agent.submit_feedback(feedback_item)
        
        result = feedback_agent.process_feedback("test_feedback_8")
        
        assert result["success"] is False
        assert "Unknown feedback type" in result["error"]
    
    def test_get_feedback_statistics(self, feedback_agent):
        """피드백 통계 조회 테스트"""
        # 다양한 피드백 제출
        feedback_items = [
            FeedbackItem(
                feedback_id="stat_feedback_1",
                workflow_id="workflow1",
                user_id="user1",
                feedback_type="bug_report",
                content="버그1",
                rating=1
            ),
            FeedbackItem(
                feedback_id="stat_feedback_2",
                workflow_id="workflow1",
                user_id="user2",
                feedback_type="feature_request",
                content="기능1",
                rating=5
            ),
            FeedbackItem(
                feedback_id="stat_feedback_3",
                workflow_id="workflow2",
                user_id="user1",
                feedback_type="general",
                content="일반1",
                rating=3
            )
        ]
        
        for item in feedback_items:
            feedback_agent.submit_feedback(item)
        
        # 통계 조회
        stats = feedback_agent.get_feedback_statistics()
        
        assert stats["total_count"] == 3
        assert "pending" in stats["status_counts"]
        assert stats["status_counts"]["pending"] == 3
        assert "bug_report" in stats["type_counts"]
        assert "feature_request" in stats["type_counts"]
        assert "general" in stats["type_counts"]
        assert stats["average_rating"] == 3.0  # (1+5+3)/3
    
    def test_get_nonexistent_feedback(self, feedback_agent):
        """존재하지 않는 피드백 조회 테스트"""
        feedback = feedback_agent.get_feedback("nonexistent")
        assert feedback is None
    
    def test_update_nonexistent_feedback_status(self, feedback_agent):
        """존재하지 않는 피드백 상태 업데이트 테스트"""
        result = feedback_agent.update_feedback_status("nonexistent", "processed")
        assert result is True  # SQLite는 UPDATE가 영향을 주지 않아도 True 반환
    
    def test_process_nonexistent_feedback(self, feedback_agent):
        """존재하지 않는 피드백 처리 테스트"""
        result = feedback_agent.process_feedback("nonexistent")
        assert result["success"] is False
        assert "Feedback not found" in result["error"] 
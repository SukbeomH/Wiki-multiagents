"""
Supervisor Agent 테스트
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agents.supervisor import SupervisorAgent, WorkflowState, AgentTask


class TestSupervisorAgent:
    """Supervisor Agent 테스트 클래스"""
    
    @pytest.fixture
    def supervisor_agent(self, tmp_path):
        """테스트용 Supervisor Agent 인스턴스"""
        workflow_dir = tmp_path / "workflows"
        return SupervisorAgent(str(workflow_dir))
    
    def test_supervisor_agent_initialization(self, supervisor_agent):
        """Supervisor Agent 초기화 테스트"""
        assert supervisor_agent is not None
        assert hasattr(supervisor_agent, 'workflow_dir')
        assert hasattr(supervisor_agent, 'active_workflows')
        assert hasattr(supervisor_agent, 'agent_registry')
        assert supervisor_agent.workflow_dir.exists()
    
    def test_register_agent(self, supervisor_agent):
        """에이전트 등록 테스트"""
        def mock_agent_func():
            return "mock_result"
        
        supervisor_agent.register_agent("test_agent", mock_agent_func)
        
        assert "test_agent" in supervisor_agent.agent_registry
        assert supervisor_agent.agent_registry["test_agent"] == mock_agent_func
    
    def test_create_workflow(self, supervisor_agent):
        """워크플로우 생성 테스트"""
        workflow_id = "test_workflow"
        steps = ["research", "extract", "retrieve"]
        
        workflow_state = supervisor_agent.create_workflow(workflow_id, steps)
        
        assert isinstance(workflow_state, WorkflowState)
        assert workflow_state.workflow_id == workflow_id
        assert workflow_state.status == "pending"
        assert workflow_state.current_step == "research"
        assert len(workflow_state.data["steps"]) == 3
        
        # active_workflows에 추가되었는지 확인
        assert workflow_id in supervisor_agent.active_workflows
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, supervisor_agent):
        """워크플로우 실행 테스트"""
        workflow_id = "test_workflow"
        steps = ["research", "extract"]
        input_data = {"query": "test query"}
        
        # 워크플로우 생성
        supervisor_agent.create_workflow(workflow_id, steps)
        
        # 워크플로우 실행
        result = await supervisor_agent.execute_workflow(workflow_id, input_data)
        
        assert isinstance(result, WorkflowState)
        assert result.status == "completed"
        assert len(result.steps_completed) == 2
        assert "research" in result.steps_completed
        assert "extract" in result.steps_completed
        assert result.data["query"] == "test query"
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(self, supervisor_agent):
        """워크플로우 실행 실패 테스트"""
        workflow_id = "test_workflow"
        steps = ["research", "unknown_step"]
        input_data = {"query": "test query"}
        
        # 워크플로우 생성
        supervisor_agent.create_workflow(workflow_id, steps)
        
        # 워크플로우 실행 (실패 예상)
        result = await supervisor_agent.execute_workflow(workflow_id, input_data)
        
        assert isinstance(result, WorkflowState)
        assert result.status == "failed"
        assert result.error is not None
        assert "unknown_step" in result.error
    
    def test_get_workflow_status(self, supervisor_agent):
        """워크플로우 상태 조회 테스트"""
        workflow_id = "test_workflow"
        steps = ["research"]
        
        # 워크플로우 생성
        supervisor_agent.create_workflow(workflow_id, steps)
        
        # 상태 조회
        status = supervisor_agent.get_workflow_status(workflow_id)
        
        assert status is not None
        assert status.workflow_id == workflow_id
        assert status.status == "pending"
    
    def test_list_workflows(self, supervisor_agent):
        """워크플로우 목록 조회 테스트"""
        # 여러 워크플로우 생성
        supervisor_agent.create_workflow("workflow1", ["research"])
        supervisor_agent.create_workflow("workflow2", ["extract"])
        
        # 전체 목록 조회
        workflows = supervisor_agent.list_workflows()
        assert len(workflows) == 2
        
        # 상태별 필터링
        pending_workflows = supervisor_agent.list_workflows(status="pending")
        assert len(pending_workflows) == 2
    
    def test_cancel_workflow(self, supervisor_agent):
        """워크플로우 취소 테스트"""
        workflow_id = "test_workflow"
        steps = ["research"]
        
        # 워크플로우 생성
        supervisor_agent.create_workflow(workflow_id, steps)
        
        # 취소
        result = supervisor_agent.cancel_workflow(workflow_id)
        assert result is True
        
        # 상태 확인
        status = supervisor_agent.get_workflow_status(workflow_id)
        assert status.status == "cancelled"
    
    def test_cleanup_completed_workflows(self, supervisor_agent):
        """완료된 워크플로우 정리 테스트"""
        # 워크플로우 생성
        supervisor_agent.create_workflow("workflow1", ["research"])
        supervisor_agent.create_workflow("workflow2", ["extract"])
        
        # 워크플로우 상태를 완료로 변경
        supervisor_agent.active_workflows["workflow1"].status = "completed"
        supervisor_agent.active_workflows["workflow2"].status = "failed"
        
        # 정리 실행
        cleaned_count = supervisor_agent.cleanup_completed_workflows(max_age_hours=0)
        
        # 즉시 정리되어야 함
        assert cleaned_count == 2
        assert len(supervisor_agent.active_workflows) == 0
    
    def test_create_workflow_with_empty_steps(self, supervisor_agent):
        """빈 단계로 워크플로우 생성 테스트"""
        workflow_id = "empty_workflow"
        steps = []
        
        workflow_state = supervisor_agent.create_workflow(workflow_id, steps)
        
        assert workflow_state.workflow_id == workflow_id
        assert workflow_state.current_step == ""
        assert len(workflow_state.data["steps"]) == 0
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_workflow(self, supervisor_agent):
        """존재하지 않는 워크플로우 실행 테스트"""
        with pytest.raises(ValueError, match="Workflow nonexistent not found"):
            await supervisor_agent.execute_workflow("nonexistent", {})
    
    def test_cancel_nonexistent_workflow(self, supervisor_agent):
        """존재하지 않는 워크플로우 취소 테스트"""
        result = supervisor_agent.cancel_workflow("nonexistent")
        assert result is False 
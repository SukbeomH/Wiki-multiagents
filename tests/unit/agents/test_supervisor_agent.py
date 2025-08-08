"""
Supervisor Agent 단위 테스트

LangGraph 기반 워크플로우 오케스트레이션 테스트
- 워크플로우 실행 흐름
- 에이전트 등록 및 호출
- 상태 관리
- 오류 처리
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.agents.supervisor.agent import SupervisorAgent, WorkflowState, AgentTask


class TestSupervisorAgent:
    """Supervisor Agent 테스트 클래스"""
    
    @pytest.fixture
    def supervisor_agent(self, tmp_path):
        """Supervisor Agent 인스턴스 생성"""
        workflow_dir = tmp_path / "workflows"
        return SupervisorAgent(workflow_dir=str(workflow_dir))
    
    @pytest.fixture
    def mock_agents(self):
        """Mock 에이전트들 생성"""
        agents = {}
        
        # Research Agent Mock
        research_mock = Mock()
        research_mock.process.return_value = {"research_data": "test_research_result"}
        agents["research"] = research_mock
        
        # Extractor Agent Mock
        extractor_mock = Mock()
        extractor_mock.process.return_value = {
            "extracted_entities": [{"text": "test_entity", "type": "PERSON"}],
            "extracted_relations": [{"subject": "A", "predicate": "relates_to", "object": "B"}]
        }
        agents["extractor"] = extractor_mock
        
        # Retriever Agent Mock
        retriever_mock = Mock()
        retriever_mock.process.return_value = {"retrieved_documents": ["doc1", "doc2"]}
        agents["retriever"] = retriever_mock
        
        # Wiki Agent Mock
        wiki_mock = Mock()
        wiki_mock.process.return_value = {"wiki_content": "test_wiki_content"}
        agents["wiki"] = wiki_mock
        
        # GraphViz Agent Mock
        graphviz_mock = Mock()
        graphviz_mock.process.return_value = {"graph_data": "test_graph_data"}
        agents["graphviz"] = graphviz_mock
        
        return agents
    
    def test_supervisor_agent_initialization(self, supervisor_agent):
        """Supervisor Agent 초기화 테스트"""
        assert supervisor_agent.workflow_dir.exists()
        assert supervisor_agent.workflow is not None
        assert isinstance(supervisor_agent.agent_registry, dict)
        assert isinstance(supervisor_agent.active_workflows, dict)
    
    def test_register_agent(self, supervisor_agent):
        """에이전트 등록 테스트"""
        mock_agent = Mock()
        
        supervisor_agent.register_agent("test_agent", mock_agent)
        
        assert "test_agent" in supervisor_agent.agent_registry
        assert supervisor_agent.agent_registry["test_agent"] == mock_agent
    
    def test_workflow_execution_success(self, supervisor_agent, mock_agents):
        """워크플로우 성공 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 워크플로우 실행
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic", "query": "test_query"}
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 결과 검증
        assert result["workflow_id"] == workflow_id
        assert result["status"] == "completed"
        assert result["current_step"] == "graphviz"
        assert len(result["steps_completed"]) == 5
        assert "research" in result["steps_completed"]
        assert "extract" in result["steps_completed"]
        assert "retrieve" in result["steps_completed"]
        assert "wiki" in result["steps_completed"]
        assert "graphviz" in result["steps_completed"]
        assert result["error"] is None
        assert "research_data" in result["data"]
        assert "extracted_entities" in result["data"]
        assert "retrieved_documents" in result["data"]
        assert "wiki_content" in result["data"]
        assert "graph_data" in result["data"]
    
    def test_workflow_execution_without_agents(self, supervisor_agent):
        """에이전트 없이 워크플로우 실행 테스트"""
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # Mock 결과로 실행되어야 함
        assert result["status"] == "completed"
        assert result["current_step"] == "graphviz"
        assert len(result["steps_completed"]) == 5
    
    def test_workflow_execution_failure(self, supervisor_agent, mock_agents):
        """워크플로우 실패 시나리오 테스트"""
        # Research Agent에서 예외 발생하도록 설정
        mock_agents["research"].process.side_effect = Exception("Research failed")
        
        supervisor_agent.register_agent("research", mock_agents["research"])
        
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 실패 상태 검증
        assert result["status"] == "failed"
        assert result["error"] == "Research failed"
        assert result["current_step"] == "research"
        assert len(result["steps_completed"]) == 0
    
    def test_get_workflow_status(self, supervisor_agent, mock_agents):
        """워크플로우 상태 조회 테스트"""
        # 에이전트 등록 및 워크플로우 실행
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        # 워크플로우 실행
        supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 상태 조회
        status = supervisor_agent.get_workflow_status(workflow_id)
        
        assert status is not None
        assert status["workflow_id"] == workflow_id
        assert status["status"] == "completed"
    
    def test_get_nonexistent_workflow_status(self, supervisor_agent):
        """존재하지 않는 워크플로우 상태 조회 테스트"""
        nonexistent_id = str(uuid.uuid4())
        status = supervisor_agent.get_workflow_status(nonexistent_id)
        
        assert status is None
    
    def test_list_workflows(self, supervisor_agent, mock_agents):
        """워크플로우 목록 조회 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 여러 워크플로우 실행
        workflow_ids = []
        for i in range(3):
            workflow_id = str(uuid.uuid4())
            workflow_ids.append(workflow_id)
            input_data = {"topic": f"test_topic_{i}"}
            supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 전체 목록 조회
        all_workflows = supervisor_agent.list_workflows()
        assert len(all_workflows) == 3
        
        # 완료된 워크플로우만 조회
        completed_workflows = supervisor_agent.list_workflows(status="completed")
        assert len(completed_workflows) == 3
        
        # 존재하지 않는 상태로 조회
        failed_workflows = supervisor_agent.list_workflows(status="failed")
        assert len(failed_workflows) == 0
    
    def test_cancel_workflow(self, supervisor_agent):
        """워크플로우 취소 테스트"""
        workflow_id = str(uuid.uuid4())
        
        # 워크플로우를 활성 상태에 추가
        supervisor_agent.active_workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "status": "running",
            "current_step": "research",
            "steps_completed": [],
            "data": {},
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 워크플로우 취소
        result = supervisor_agent.cancel_workflow(workflow_id)
        
        assert result is True
        assert supervisor_agent.active_workflows[workflow_id]["status"] == "cancelled"
    
    def test_cancel_nonexistent_workflow(self, supervisor_agent):
        """존재하지 않는 워크플로우 취소 테스트"""
        nonexistent_id = str(uuid.uuid4())
        result = supervisor_agent.cancel_workflow(nonexistent_id)
        
        assert result is False
    
    def test_process_method(self, supervisor_agent, mock_agents):
        """process 메서드 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 입력 데이터 생성
        from src.core.schemas.agents import SupervisorIn
        input_data = SupervisorIn(
            trace_id="test_trace_id",
            user_id="test_user_id",
            request={
                "topic": "test_topic",
                "query": "test_query",
                "extraction_mode": "comprehensive"
            }
        )
        
        # 처리 실행
        result = supervisor_agent.process(input_data)
        
        # 결과 검증
        assert result.workflow_id is not None
        assert result.status == "completed"
        assert result.current_step == "graphviz"
        assert len(result.steps_completed) == 5
        assert result.error is None
        assert "research_data" in result.data
        assert "extracted_entities" in result.data
        assert "retrieved_documents" in result.data
        assert "wiki_content" in result.data
        assert "graph_data" in result.data
    
    def test_process_method_failure(self, supervisor_agent, mock_agents):
        """process 메서드 실패 시나리오 테스트"""
        # Research Agent에서 예외 발생
        mock_agents["research"].process.side_effect = Exception("Processing failed")
        supervisor_agent.register_agent("research", mock_agents["research"])
        
        # 입력 데이터 생성
        from src.core.schemas.agents import SupervisorIn
        input_data = SupervisorIn(
            trace_id="test_trace_id",
            user_id="test_user_id",
            request={
                "topic": "test_topic",
                "query": "test_query",
                "extraction_mode": "comprehensive"
            }
        )
        
        # 처리 실행
        result = supervisor_agent.process(input_data)
        
        # 실패 결과 검증
        assert result.workflow_id is not None
        assert result.status == "failed"
        assert result.error == "Processing failed"
        assert len(result.steps_completed) == 0
    
    def test_health_check(self, supervisor_agent):
        """상태 확인 테스트"""
        health_info = supervisor_agent.health_check()
        
        assert health_info["status"] == "healthy"
        assert health_info["agent_type"] == "supervisor"
        assert "timestamp" in health_info
        assert "config" in health_info
        assert health_info["config"]["workflow_dir"] == str(supervisor_agent.workflow_dir)
        assert "registered_agents" in health_info["config"]
        assert "workflow_steps" in health_info["config"]
    
    def test_workflow_steps_execution_order(self, supervisor_agent, mock_agents):
        """워크플로우 단계 실행 순서 테스트"""
        # 각 단계에서 호출 여부를 추적하는 Mock 생성
        step_calls = []
        
        # 실제 agent.process()가 호출되므로, 각 mock의 process에 사이드이펙트를 주입해 순서를 기록
        for name in ["research", "extractor", "retriever", "wiki", "graphviz"]:
            agent = mock_agents.get(name)
            if agent is None:
                continue
            def make_side_effect(step_name):
                def _side_effect(*args, **kwargs):
                    step_calls.append(step_name)
                    return agent.process.return_value if hasattr(agent, "process") else {}
                return _side_effect
            agent.process.side_effect = make_side_effect("research" if name=="research" else ("extract" if name=="extractor" else ("retrieve" if name=="retriever" else ("wiki" if name=="wiki" else "graphviz"))))
        
        # Mock 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 워크플로우 실행
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 실행 순서 검증
        expected_order = ["research", "extract", "retrieve", "wiki", "graphviz"]
        assert len(step_calls) == len(expected_order)
        for i, step in enumerate(expected_order):
            assert step_calls[i] == step
    
    def test_workflow_state_persistence(self, supervisor_agent, mock_agents):
        """워크플로우 상태 지속성 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        # 워크플로우 실행
        result1 = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 상태 조회
        result2 = supervisor_agent.get_workflow_status(workflow_id)
        
        # 두 결과가 동일한지 검증
        assert result1["workflow_id"] == result2["workflow_id"]
        assert result1["status"] == result2["status"]
        assert result1["current_step"] == result2["current_step"]
        assert result1["steps_completed"] == result2["steps_completed"]
        assert result1["data"] == result2["data"] 
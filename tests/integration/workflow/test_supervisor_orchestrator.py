"""
Supervisor Orchestrator 통합 테스트

LangGraph 기반 워크플로우 오케스트레이션 통합 테스트
- 전체 워크플로우 실행 흐름
- 에이전트 간 연동
- 오류 처리 및 복구
- 상태 관리 및 지속성
"""

import pytest
import time
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.agents.supervisor.agent import SupervisorAgent
from src.core.utils.lock_manager import LockManager
from src.core.utils.retry_manager import RetryManager
from src.core.utils.checkpoint_manager import CheckpointManager
from src.core.schemas.agents import SupervisorIn


class TestSupervisorOrchestratorIntegration:
    """Supervisor Orchestrator 통합 테스트 클래스"""
    
    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """임시 디렉토리들 생성"""
        return {
            "workflow_dir": tmp_path / "workflows",
            "lock_dir": tmp_path / "locks",
            "checkpoint_dir": tmp_path / "checkpoints"
        }
    
    @pytest.fixture
    def supervisor_agent(self, temp_dirs):
        """Supervisor Agent 인스턴스 생성"""
        return SupervisorAgent(workflow_dir=str(temp_dirs["workflow_dir"]))
    
    @pytest.fixture
    def lock_manager(self, temp_dirs):
        """LockManager 인스턴스 생성"""
        return LockManager(lock_dir=str(temp_dirs["lock_dir"]))
    
    @pytest.fixture
    def retry_manager(self):
        """RetryManager 인스턴스 생성"""
        return RetryManager(max_retries=2, base_delay=0.1)
    
    @pytest.fixture
    def checkpoint_manager(self, temp_dirs):
        """CheckpointManager 인스턴스 생성"""
        return CheckpointManager(checkpoint_dir=str(temp_dirs["checkpoint_dir"]))
    
    @pytest.fixture
    def mock_agents(self):
        """Mock 에이전트들 생성"""
        agents = {}
        
        # Research Agent Mock
        research_mock = Mock()
        research_mock.process.return_value = {
            "research_data": "test_research_result",
            "sources": ["source1", "source2"],
            "summary": "Test research summary"
        }
        agents["research"] = research_mock
        
        # Extractor Agent Mock
        extractor_mock = Mock()
        extractor_mock.process.return_value = {
            "extracted_entities": [
                {"text": "test_entity_1", "type": "PERSON", "confidence": 0.9},
                {"text": "test_entity_2", "type": "ORGANIZATION", "confidence": 0.8}
            ],
            "extracted_relations": [
                {"subject": "test_entity_1", "predicate": "works_for", "object": "test_entity_2"}
            ]
        }
        agents["extractor"] = extractor_mock
        
        # Retriever Agent Mock
        retriever_mock = Mock()
        retriever_mock.process.return_value = {
            "retrieved_documents": [
                {"id": "doc1", "content": "Test document 1", "score": 0.95},
                {"id": "doc2", "content": "Test document 2", "score": 0.87}
            ]
        }
        agents["retriever"] = retriever_mock
        
        # Wiki Agent Mock
        wiki_mock = Mock()
        wiki_mock.process.return_value = {
            "wiki_content": "# Test Wiki Page\n\nThis is a test wiki page content.",
            "metadata": {"title": "Test Wiki", "created_at": datetime.now().isoformat()}
        }
        agents["wiki"] = wiki_mock
        
        # GraphViz Agent Mock
        graphviz_mock = Mock()
        graphviz_mock.process.return_value = {
            "graph_data": {
                "nodes": [{"id": "node1", "label": "Test Node"}],
                "edges": [{"source": "node1", "target": "node2", "label": "relates_to"}]
            }
        }
        agents["graphviz"] = graphviz_mock
        
        return agents
    
    def test_complete_workflow_execution(self, supervisor_agent, mock_agents):
        """전체 워크플로우 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 워크플로우 실행
        workflow_id = str(uuid.uuid4())
        input_data = {
            "topic": "test_topic",
            "query": "test_query",
            "extraction_mode": "comprehensive"
        }
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 결과 검증
        assert result["workflow_id"] == workflow_id
        assert result["status"] == "completed"
        assert result["current_step"] == "graphviz"
        assert len(result["steps_completed"]) == 5
        
        # 각 단계별 데이터 검증
        assert "research_data" in result["data"]
        assert "extracted_entities" in result["data"]
        assert "retrieved_documents" in result["data"]
        assert "wiki_content" in result["data"]
        assert "graph_data" in result["data"]
        
        # 에이전트 호출 검증
        for agent_type, agent in mock_agents.items():
            assert agent.process.called
    
    def test_workflow_with_lock_management(self, supervisor_agent, lock_manager, mock_agents):
        """락 관리와 함께 워크플로우 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        lock_name = f"workflow_{workflow_id}"
        
        # 락 획득 후 워크플로우 실행
        with lock_manager.lock_context(lock_name):
            input_data = {"topic": "test_topic"}
            result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 결과 검증
        assert result["status"] == "completed"
        assert not lock_manager.is_locked(lock_name)  # 락이 해제되어야 함
    
    def test_workflow_with_retry_logic(self, supervisor_agent, retry_manager, mock_agents):
        """재시도 로직과 함께 워크플로우 실행 테스트"""
        # Research Agent에서 일시적 실패 후 성공하도록 설정
        call_count = 0
        def failing_then_success_research():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network error")
            return {"research_data": "successful_research_result"}
        
        mock_agents["research"].process.side_effect = failing_then_success_research
        supervisor_agent.register_agent("research", mock_agents["research"])
        
        # 재시도 로직으로 워크플로우 실행
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        def execute_workflow_with_retry():
            return supervisor_agent.execute_workflow(workflow_id, input_data)
        
        result = retry_manager.retry(execute_workflow_with_retry)
        
        # 결과 검증
        assert result["status"] == "completed"
        assert call_count == 3  # 2번 실패 후 3번째 성공
    
    def test_workflow_with_checkpoint_management(self, supervisor_agent, checkpoint_manager, mock_agents):
        """체크포인트 관리와 함께 워크플로우 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        initial_state = {"topic": "test_topic", "status": "starting"}
        
        # 체크포인트 컨텍스트와 함께 워크플로우 실행
        with checkpoint_manager.checkpoint_context(workflow_id, initial_state):
            input_data = {"topic": "test_topic"}
            result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 결과 검증
        assert result["status"] == "completed"
        
        # 체크포인트 확인
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 1
        assert checkpoints[0].state == initial_state
    
    def test_workflow_failure_and_rollback(self, supervisor_agent, checkpoint_manager, mock_agents):
        """워크플로우 실패 및 롤백 테스트"""
        # Research Agent에서 예외 발생하도록 설정
        mock_agents["research"].process.side_effect = Exception("Research failed")
        supervisor_agent.register_agent("research", mock_agents["research"])
        
        workflow_id = str(uuid.uuid4())
        initial_state = {"topic": "test_topic", "status": "starting"}
        
        # 체크포인트 생성
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, initial_state)
        
        try:
            # 워크플로우 실행 (실패 예상)
            input_data = {"topic": "test_topic"}
            result = supervisor_agent.execute_workflow(workflow_id, input_data)
        except Exception:
            # 실패 시 롤백
            rollback_state = checkpoint_manager.rollback_to_checkpoint(workflow_id, checkpoint_id)
            assert rollback_state == initial_state
        else:
            pytest.fail("Expected workflow to fail")
    
    def test_concurrent_workflow_execution(self, supervisor_agent, lock_manager, mock_agents):
        """동시 워크플로우 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def execute_workflow_thread(workflow_id, lock_name):
            try:
                with lock_manager.lock_context(lock_name):
                    input_data = {"topic": f"test_topic_{workflow_id}"}
                    result = supervisor_agent.execute_workflow(workflow_id, input_data)
                    results.put((workflow_id, result))
            except Exception as e:
                errors.put((workflow_id, e))
        
        # 여러 워크플로우 동시 실행
        threads = []
        for i in range(3):
            workflow_id = str(uuid.uuid4())
            lock_name = f"workflow_{workflow_id}"
            thread = threading.Thread(
                target=execute_workflow_thread,
                args=(workflow_id, lock_name)
            )
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 검증
        assert results.qsize() == 3
        assert errors.qsize() == 0
        
        # 모든 워크플로우가 성공했는지 확인
        while not results.empty():
            workflow_id, result = results.get()
            assert result["status"] == "completed"
    
    def test_workflow_with_error_recovery(self, supervisor_agent, retry_manager, checkpoint_manager, mock_agents):
        """오류 복구와 함께 워크플로우 실행 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        initial_state = {"topic": "test_topic", "status": "starting"}
        
        # 체크포인트 생성
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, initial_state)
        
        # 일시적 실패 후 성공하는 함수
        call_count = 0
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary error")
            return {"data": "success"}
        
        mock_agents["research"].process.side_effect = failing_then_success
        
        # 재시도 로직으로 워크플로우 실행
        def execute_workflow_with_recovery():
            try:
                input_data = {"topic": "test_topic"}
                return supervisor_agent.execute_workflow(workflow_id, input_data)
            except Exception:
                # 실패 시 롤백 후 재시도
                checkpoint_manager.rollback_to_checkpoint(workflow_id, checkpoint_id)
                raise
        
        result = retry_manager.retry(execute_workflow_with_recovery)
        
        # 결과 검증
        assert result["status"] == "completed"
        assert call_count == 3
    
    def test_workflow_state_persistence(self, supervisor_agent, checkpoint_manager, mock_agents):
        """워크플로우 상태 지속성 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        workflow_id = str(uuid.uuid4())
        
        # 워크플로우 실행
        input_data = {"topic": "test_topic"}
        result1 = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 상태 조회
        result2 = supervisor_agent.get_workflow_status(workflow_id)
        
        # 두 결과가 동일한지 검증
        assert result1["workflow_id"] == result2["workflow_id"]
        assert result1["status"] == result2["status"]
        assert result1["current_step"] == result2["current_step"]
        assert result1["steps_completed"] == result2["steps_completed"]
        assert result1["data"] == result2["data"]
    
    def test_workflow_cancellation(self, supervisor_agent, mock_agents):
        """워크플로우 취소 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
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
    
    def test_workflow_listing_and_filtering(self, supervisor_agent, mock_agents):
        """워크플로우 목록 조회 및 필터링 테스트"""
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
        
        # 실행 중인 워크플로우 조회
        running_workflows = supervisor_agent.list_workflows(status="running")
        assert len(running_workflows) == 0
    
    def test_supervisor_agent_health_check(self, supervisor_agent):
        """Supervisor Agent 상태 확인 테스트"""
        health_info = supervisor_agent.health_check()
        
        assert health_info["status"] == "healthy"
        assert health_info["agent_type"] == "supervisor"
        assert "timestamp" in health_info
        assert "config" in health_info
        assert "workflow_dir" in health_info["config"]
        assert "registered_agents" in health_info["config"]
        assert "workflow_steps" in health_info["config"]
    
    def test_process_method_integration(self, supervisor_agent, mock_agents):
        """process 메서드 통합 테스트"""
        # 에이전트 등록
        for agent_type, agent in mock_agents.items():
            supervisor_agent.register_agent(agent_type, agent)
        
        # 입력 데이터 생성
        input_data = SupervisorIn(
            topic="test_topic",
            query="test_query",
            extraction_mode="comprehensive"
        )
        
        # 처리 실행
        result = supervisor_agent.process(input_data)
        
        # 결과 검증
        assert result.workflow_id is not None
        assert result.status == "completed"
        assert result.current_step == "graphviz"
        assert len(result.steps_completed) == 5
        assert result.error is None
        
        # 데이터 검증
        assert "research_data" in result.data
        assert "extracted_entities" in result.data
        assert "retrieved_documents" in result.data
        assert "wiki_content" in result.data
        assert "graph_data" in result.data


class TestSupervisorOrchestratorErrorHandling:
    """Supervisor Orchestrator 오류 처리 테스트"""
    
    @pytest.fixture
    def supervisor_agent(self, tmp_path):
        """Supervisor Agent 인스턴스 생성"""
        workflow_dir = tmp_path / "workflows"
        return SupervisorAgent(workflow_dir=str(workflow_dir))
    
    def test_workflow_with_agent_failure(self, supervisor_agent):
        """에이전트 실패 시 워크플로우 처리 테스트"""
        # Research Agent에서 예외 발생
        mock_research = Mock()
        mock_research.process.side_effect = Exception("Research agent failed")
        supervisor_agent.register_agent("research", mock_research)
        
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 실패 상태 검증
        assert result["status"] == "failed"
        assert result["error"] == "Research agent failed"
        assert result["current_step"] == "research"
        assert len(result["steps_completed"]) == 0
    
    def test_workflow_with_missing_agents(self, supervisor_agent):
        """에이전트가 없는 경우 워크플로우 처리 테스트"""
        workflow_id = str(uuid.uuid4())
        input_data = {"topic": "test_topic"}
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # Mock 결과로 실행되어야 함
        assert result["status"] == "completed"
        assert result["current_step"] == "graphviz"
        assert len(result["steps_completed"]) == 5
    
    def test_workflow_with_invalid_input(self, supervisor_agent):
        """잘못된 입력으로 워크플로우 처리 테스트"""
        workflow_id = str(uuid.uuid4())
        input_data = None  # 잘못된 입력
        
        result = supervisor_agent.execute_workflow(workflow_id, input_data)
        
        # 오류 처리되어야 함
        assert result["status"] == "failed"
        assert result["error"] is not None
    
    def test_workflow_with_process_method_failure(self, supervisor_agent):
        """process 메서드 실패 시나리오 테스트"""
        # Research Agent에서 예외 발생
        mock_research = Mock()
        mock_research.process.side_effect = Exception("Processing failed")
        supervisor_agent.register_agent("research", mock_research)
        
        # 입력 데이터 생성
        input_data = SupervisorIn(
            topic="test_topic",
            query="test_query",
            extraction_mode="comprehensive"
        )
        
        # 처리 실행
        result = supervisor_agent.process(input_data)
        
        # 실패 결과 검증
        assert result.workflow_id is not None
        assert result.status == "failed"
        assert result.error == "Processing failed"
        assert len(result.steps_completed) == 0 
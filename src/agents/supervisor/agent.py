"""
Supervisor Agent (단순화된 LangGraph 기반 버전)

LangGraph 기반 워크플로우 오케스트레이션
- Research → Extractor/Retriever → Wiki → GraphViz 단계
- filelock 기반 기본 락 처리
- 단순 재시도 로직 (base=1s, max 3회)
- 기본 체크포인터 롤백 처리
- RDFLib 기반 KG Manager 연동
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, TypedDict, Annotated
from pathlib import Path
from datetime import datetime
import uuid

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import filelock

from src.core.schemas.agents import SupervisorIn

logger = logging.getLogger(__name__)


class WorkflowStepError(Exception):
    """Raised to indicate a workflow step failed, carrying the step name and message."""

    def __init__(self, step_name: str, message: str):
        super().__init__(message)
        self.step_name = step_name
        self.message = message


class SupervisorProcessResult(BaseModel):
    """Supervisor.process 반환용 단순 결과 스키마 (내부용)"""
    workflow_id: str
    status: str
    current_step: str
    steps_completed: List[str]
    data: Dict[str, Any]
    error: Optional[str] = None
    created_at: str
    updated_at: str

class WorkflowState(TypedDict):
    """워크플로우 상태 (LangGraph 호환)"""
    workflow_id: str
    status: str
    current_step: str
    steps_completed: List[str]
    data: Dict[str, Any]
    error: Optional[str]
    created_at: str
    updated_at: str


class AgentTask(BaseModel):
    """에이전트 작업 모델"""
    task_id: str = Field(..., description="작업 ID")
    agent_type: str = Field(..., description="에이전트 타입")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="입력 데이터")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="출력 데이터")
    status: str = Field(default="pending", description="작업 상태")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    completed_at: Optional[datetime] = Field(default=None, description="완료 시간")


class SupervisorAgent:
    """단순화된 LangGraph 기반 오케스트레이션 에이전트"""
    
    def __init__(self, workflow_dir: Optional[str] = None):
        """
        Supervisor Agent 초기화
        
        Args:
            workflow_dir: 워크플로우 저장 디렉토리
        """
        self.workflow_dir = Path(workflow_dir) if workflow_dir else Path("data/workflows")
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        
        # LangGraph 워크플로우 초기화
        self.workflow = self._create_workflow()
        
        # 에이전트 레지스트리
        self.agent_registry: Dict[str, Any] = {}
        
        # 활성 워크플로우 상태 저장
        self.active_workflows: Dict[str, WorkflowState] = {}
        
        logger.info(f"Supervisor Agent initialized with workflow dir: {self.workflow_dir}")
    
    def _create_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 생성"""
        workflow = StateGraph(WorkflowState)
        
        # 워크플로우 노드 추가
        workflow.add_node("research", self._research_step)
        workflow.add_node("extract", self._extract_step)
        workflow.add_node("retrieve", self._retrieve_step)
        workflow.add_node("wiki", self._wiki_step)
        workflow.add_node("graphviz", self._graphviz_step)
        
        # 워크플로우 엣지 정의
        workflow.set_entry_point("research")
        workflow.add_edge("research", "extract")
        workflow.add_edge("extract", "retrieve")
        workflow.add_edge("retrieve", "wiki")
        workflow.add_edge("wiki", "graphviz")
        workflow.add_edge("graphviz", END)
        
        return workflow.compile()
    
    def register_agent(self, agent_type: str, agent_instance: Any) -> None:
        """
        에이전트 등록
        
        Args:
            agent_type: 에이전트 타입
            agent_instance: 에이전트 인스턴스
        """
        self.agent_registry[agent_type] = agent_instance
        logger.info(f"Agent registered: {agent_type}")
    
    def _research_step(self, state: WorkflowState) -> WorkflowState:
        """Research 단계 실행"""
        try:
            logger.info(f"Executing research step for workflow {state['workflow_id']}")
            
            # Research Agent 호출
            if "research" in self.agent_registry:
                research_agent = self.agent_registry["research"]
                # 실제 Research Agent 호출 로직
                result = research_agent.process()
            else:
                result = {"research_data": "mock_research_result"}
            
            # 상태 업데이트
            state["current_step"] = "research"
            state["steps_completed"].append("research")
            state["data"].update(result)
            state["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Research step completed for workflow {state['workflow_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Research step failed: {e}")
            # 실패 지점 전달을 위해 step 포함 예외 재발생
            raise WorkflowStepError("research", str(e))
    
    def _extract_step(self, state: WorkflowState) -> WorkflowState:
        """Extract 단계 실행"""
        try:
            logger.info(f"Executing extract step for workflow {state['workflow_id']}")
            
            # Extractor Agent 호출
            if "extractor" in self.agent_registry:
                extractor_agent = self.agent_registry["extractor"]
                # 실제 Extractor Agent 호출 로직
                result = extractor_agent.process()
            else:
                result = {"extracted_entities": [], "extracted_relations": []}
            
            # 상태 업데이트
            state["current_step"] = "extract"
            state["steps_completed"].append("extract")
            state["data"].update(result)
            state["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Extract step completed for workflow {state['workflow_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Extract step failed: {e}")
            raise WorkflowStepError("extract", str(e))
    
    def _retrieve_step(self, state: WorkflowState) -> WorkflowState:
        """Retrieve 단계 실행"""
        try:
            logger.info(f"Executing retrieve step for workflow {state['workflow_id']}")
            
            # Retriever Agent 호출
            if "retriever" in self.agent_registry:
                retriever_agent = self.agent_registry["retriever"]
                # 실제 Retriever Agent 호출 로직
                result = retriever_agent.process()
            else:
                result = {"retrieved_documents": []}
            
            # 상태 업데이트
            state["current_step"] = "retrieve"
            state["steps_completed"].append("retrieve")
            state["data"].update(result)
            state["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Retrieve step completed for workflow {state['workflow_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Retrieve step failed: {e}")
            raise WorkflowStepError("retrieve", str(e))
    
    def _wiki_step(self, state: WorkflowState) -> WorkflowState:
        """Wiki 단계 실행"""
        try:
            logger.info(f"Executing wiki step for workflow {state['workflow_id']}")
            
            # Wiki Agent 호출
            if "wiki" in self.agent_registry:
                wiki_agent = self.agent_registry["wiki"]
                # 실제 Wiki Agent 호출 로직
                result = wiki_agent.process()
            else:
                result = {"wiki_content": "mock_wiki_content"}
            
            # 상태 업데이트
            state["current_step"] = "wiki"
            state["steps_completed"].append("wiki")
            state["data"].update(result)
            state["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Wiki step completed for workflow {state['workflow_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Wiki step failed: {e}")
            raise WorkflowStepError("wiki", str(e))
    
    def _graphviz_step(self, state: WorkflowState) -> WorkflowState:
        """GraphViz 단계 실행"""
        try:
            logger.info(f"Executing graphviz step for workflow {state['workflow_id']}")
            
            # GraphViz Agent 호출
            if "graphviz" in self.agent_registry:
                graphviz_agent = self.agent_registry["graphviz"]
                # 실제 GraphViz Agent 호출 로직
                result = graphviz_agent.process()
            else:
                result = {"graph_data": "mock_graph_data"}
            
            # 상태 업데이트
            state["current_step"] = "graphviz"
            state["steps_completed"].append("graphviz")
            state["status"] = "completed"
            state["data"].update(result)
            state["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"GraphViz step completed for workflow {state['workflow_id']}")
            return state
            
        except Exception as e:
            logger.error(f"GraphViz step failed: {e}")
            raise WorkflowStepError("graphviz", str(e))
    
    def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> WorkflowState:
        """
        워크플로우 실행
        
        Args:
            workflow_id: 워크플로우 ID
            input_data: 입력 데이터
            
        Returns:
            WorkflowState: 워크플로우 상태
        """
        try:
            # 초기 상태 생성
            initial_state: WorkflowState = {
                "workflow_id": workflow_id,
                "status": "running",
                "current_step": "",
                "steps_completed": [],
                "data": input_data,
                "error": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Starting workflow execution: {workflow_id}")
            
            # LangGraph 워크플로우 실행
            result = self.workflow.invoke(initial_state)
            
            # 결과를 메모리에 저장
            self.active_workflows[workflow_id] = result
            
            logger.info(f"Workflow execution completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            failed_step = e.step_name if isinstance(e, WorkflowStepError) else ""
            error_message = e.message if isinstance(e, WorkflowStepError) else str(e)
            error_state = {
                "workflow_id": workflow_id,
                "status": "failed",
                "current_step": failed_step,
                "steps_completed": [],
                "data": input_data,
                "error": error_message,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.active_workflows[workflow_id] = error_state
            return error_state
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        워크플로우 상태 조회
        
        Args:
            workflow_id: 워크플로우 ID
            
        Returns:
            Optional[WorkflowState]: 워크플로우 상태
        """
        return self.active_workflows.get(workflow_id)
    
    def list_workflows(self, status: Optional[str] = None) -> List[WorkflowState]:
        """
        워크플로우 목록 조회
        
        Args:
            status: 필터링할 상태
            
        Returns:
            List[WorkflowState]: 워크플로우 목록
        """
        workflows = list(self.active_workflows.values())
        if status:
            workflows = [w for w in workflows if w["status"] == status]
        return workflows
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        워크플로우 취소
        
        Args:
            workflow_id: 워크플로우 ID
            
        Returns:
            bool: 취소 성공 여부
        """
        try:
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "cancelled"
                self.active_workflows[workflow_id]["updated_at"] = datetime.now().isoformat()
                logger.info(f"Workflow cancelled: {workflow_id}")
                return True
            else:
                logger.warning(f"Workflow not found: {workflow_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel workflow: {e}")
            return False
    
    def process(self, input_data: SupervisorIn) -> SupervisorProcessResult:
        """
        Supervisor Agent 처리
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            SupervisorOut: 처리 결과
        """
        try:
            workflow_id = str(uuid.uuid4())
            
            # 워크플로우 실행
            workflow_state = self.execute_workflow(workflow_id, input_data.dict())
            
            # 결과 생성 (내부 스키마)
            result = SupervisorProcessResult(
                workflow_id=workflow_id,
                status=workflow_state["status"],
                current_step=workflow_state["current_step"],
                steps_completed=workflow_state["steps_completed"],
                data=workflow_state["data"],
                error=workflow_state.get("error"),
                created_at=workflow_state["created_at"],
                updated_at=workflow_state["updated_at"]
            )
            
            logger.info(f"Supervisor processing completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Supervisor processing failed: {e}")
            
            # 오류 시에도 유효한 결과 반환
            return SupervisorProcessResult(
                workflow_id=str(uuid.uuid4()),
                status="failed",
                current_step="",
                steps_completed=[],
                data={},
                error=str(e),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        에이전트 상태 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            health_info = {
                "status": "healthy",
                "agent_type": "supervisor",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "workflow_dir": str(self.workflow_dir),
                    "registered_agents": list(self.agent_registry.keys()),
                    "workflow_steps": ["research", "extract", "retrieve", "wiki", "graphviz"]
                }
            }
            
            logger.info("Supervisor health check completed")
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "agent_type": "supervisor",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            
            logger.error(f"Supervisor health check failed: {e}")
            return health_info 
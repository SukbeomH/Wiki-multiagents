"""
Supervisor Agent Implementation

오케스트레이션을 담당하는 에이전트
- LangGraph 워크플로우
- Redis Redlock
- 에이전트 간 조율
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import os

from pydantic import BaseModel, Field

from src.core.schemas.agents import SupervisorIn, SupervisorOut

logger = logging.getLogger(__name__)


class WorkflowState(BaseModel):
    """워크플로우 상태 모델"""
    workflow_id: str = Field(..., description="워크플로우 ID")
    status: str = Field(default="pending", description="워크플로우 상태")
    current_step: str = Field(default="", description="현재 단계")
    steps_completed: List[str] = Field(default_factory=list, description="완료된 단계들")
    data: Dict[str, Any] = Field(default_factory=dict, description="워크플로우 데이터")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.now, description="업데이트 시간")
    error: Optional[str] = Field(default=None, description="오류 메시지")


class AgentTask(BaseModel):
    """에이전트 작업 모델"""
    task_id: str = Field(..., description="작업 ID")
    agent_type: str = Field(..., description="에이전트 타입")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="입력 데이터")
    output_data: Optional[Dict[str, Any]] = Field(default=None, description="출력 데이터")
    status: str = Field(default="pending", description="작업 상태")
    priority: int = Field(default=1, description="우선순위")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    completed_at: Optional[datetime] = Field(default=None, description="완료 시간")


class SupervisorAgent:
    """오케스트레이션을 담당하는 에이전트"""
    
    def __init__(self, workflow_dir: Optional[str] = None):
        """
        Supervisor Agent 초기화
        
        Args:
            workflow_dir: 워크플로우 저장 디렉토리
        """
        self.workflow_dir = Path(workflow_dir) if workflow_dir else Path("data/workflows")
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.agent_registry: Dict[str, Callable] = {}
        self.lock_manager = None  # Redis Redlock 매니저
        
        logger.info(f"Supervisor Agent initialized with workflow dir: {self.workflow_dir}")
    
    def register_agent(self, agent_type: str, agent_func: Callable) -> None:
        """
        에이전트 등록
        
        Args:
            agent_type: 에이전트 타입
            agent_func: 에이전트 함수
        """
        self.agent_registry[agent_type] = agent_func
        logger.info(f"Agent registered: {agent_type}")
    
    def create_workflow(self, workflow_id: str, steps: List[str]) -> WorkflowState:
        """
        워크플로우 생성
        
        Args:
            workflow_id: 워크플로우 ID
            steps: 워크플로우 단계들
            
        Returns:
            WorkflowState: 생성된 워크플로우 상태
        """
        try:
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                status="pending",
                current_step=steps[0] if steps else "",
                data={"steps": steps, "total_steps": len(steps)}
            )
            
            self.active_workflows[workflow_id] = workflow_state
            logger.info(f"Workflow created: {workflow_id} with {len(steps)} steps")
            return workflow_state
            
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_id}: {e}")
            raise
    
    async def execute_workflow(self, workflow_id: str, input_data: Dict[str, Any]) -> WorkflowState:
        """
        워크플로우 실행
        
        Args:
            workflow_id: 워크플로우 ID
            input_data: 입력 데이터
            
        Returns:
            WorkflowState: 실행 결과
        """
        try:
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            workflow = self.active_workflows[workflow_id]
            workflow.status = "running"
            workflow.data.update(input_data)
            workflow.updated_at = datetime.now()
            
            steps = workflow.data.get("steps", [])
            
            for step in steps:
                if workflow.status == "failed":
                    break
                
                workflow.current_step = step
                workflow.updated_at = datetime.now()
                
                logger.info(f"Executing step: {step} for workflow {workflow_id}")
                
                # 단계 실행
                try:
                    result = await self._execute_step(step, workflow.data)
                    workflow.data[f"step_{step}_result"] = result
                    workflow.steps_completed.append(step)
                    
                except Exception as e:
                    workflow.status = "failed"
                    workflow.error = f"Step {step} failed: {str(e)}"
                    logger.error(f"Step {step} failed: {e}")
                    break
            
            if workflow.status == "running":
                workflow.status = "completed"
                workflow.current_step = ""
            
            workflow.updated_at = datetime.now()
            logger.info(f"Workflow {workflow_id} completed with status: {workflow.status}")
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].status = "failed"
                self.active_workflows[workflow_id].error = str(e)
            raise
    
    async def _execute_step(self, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        단계 실행
        
        Args:
            step: 실행할 단계
            data: 워크플로우 데이터
            
        Returns:
            Dict[str, Any]: 단계 실행 결과
        """
        try:
            # 단계별 실행 로직
            if step == "research":
                return await self._execute_research_step(data)
            elif step == "extract":
                return await self._execute_extract_step(data)
            elif step == "retrieve":
                return await self._execute_retrieve_step(data)
            elif step == "wiki":
                return await self._execute_wiki_step(data)
            elif step == "graphviz":
                return await self._execute_graphviz_step(data)
            elif step == "feedback":
                return await self._execute_feedback_step(data)
            else:
                raise ValueError(f"Unknown step: {step}")
                
        except Exception as e:
            logger.error(f"Failed to execute step {step}: {e}")
            raise
    
    async def _execute_research_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Research 단계 실행"""
        # 실제로는 Research Agent 호출
        logger.info("Executing research step")
        return {"research_results": "sample research data"}
    
    async def _execute_extract_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract 단계 실행"""
        # 실제로는 Extractor Agent 호출
        logger.info("Executing extract step")
        return {"extracted_entities": ["entity1", "entity2"]}
    
    async def _execute_retrieve_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve 단계 실행"""
        # 실제로는 Retriever Agent 호출
        logger.info("Executing retrieve step")
        return {"retrieved_documents": ["doc1", "doc2"]}
    
    async def _execute_wiki_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Wiki 단계 실행"""
        # 실제로는 Wiki Agent 호출
        logger.info("Executing wiki step")
        return {"wiki_content": "sample wiki content"}
    
    async def _execute_graphviz_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """GraphViz 단계 실행"""
        # 실제로는 GraphViz Agent 호출
        logger.info("Executing graphviz step")
        return {"graph_data": {"nodes": [], "edges": []}}
    
    async def _execute_feedback_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Feedback 단계 실행"""
        # 실제로는 Feedback Agent 호출
        logger.info("Executing feedback step")
        return {"feedback": "sample feedback"}
    
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
            workflows = [w for w in workflows if w.status == status]
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
                workflow = self.active_workflows[workflow_id]
                if workflow.status in ["pending", "running"]:
                    workflow.status = "cancelled"
                    workflow.updated_at = datetime.now()
                    logger.info(f"Workflow {workflow_id} cancelled")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """
        완료된 워크플로우 정리
        
        Args:
            max_age_hours: 최대 보관 시간 (시간)
            
        Returns:
            int: 정리된 워크플로우 수
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            workflows_to_remove = []
            
            for workflow_id, workflow in self.active_workflows.items():
                if (workflow.status in ["completed", "failed", "cancelled"] and 
                    workflow.updated_at < cutoff_time):
                    workflows_to_remove.append(workflow_id)
            
            for workflow_id in workflows_to_remove:
                del self.active_workflows[workflow_id]
            
            logger.info(f"Cleaned up {len(workflows_to_remove)} completed workflows")
            return len(workflows_to_remove)
            
        except Exception as e:
            logger.error(f"Failed to cleanup workflows: {e}")
            return 0
    
    def process(self, input_data: SupervisorIn) -> SupervisorOut:
        """
        Supervisor Agent 메인 처리 함수
        
        Args:
            input_data: SupervisorIn 입력 데이터
            
        Returns:
            SupervisorOut: 워크플로우 실행 결과
        """
        try:
            logger.info(f"Supervisor processing started: {input_data.workflow_id}")
            
            # 워크플로우 생성
            workflow_state = self.create_workflow(
                workflow_id=input_data.workflow_id,
                steps=input_data.workflow_steps
            )
            
            # 워크플로우 실행 (비동기 실행을 동기로 래핑)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_state = loop.run_until_complete(
                    self.execute_workflow(input_data.workflow_id, input_data.input_data)
                )
            finally:
                loop.close()
            
            # 결과 반환
            result = SupervisorOut(
                workflow_id=result_state.workflow_id,
                status=result_state.status,
                current_step=result_state.current_step,
                steps_completed=result_state.steps_completed,
                data=result_state.data,
                success=result_state.status == "completed",
                error=result_state.error
            )
            
            logger.info(f"Supervisor processing completed: {input_data.workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Supervisor processing failed: {e}")
            return SupervisorOut(
                workflow_id=input_data.workflow_id,
                status="failed",
                current_step="",
                steps_completed=[],
                data={},
                success=False,
                error=str(e)
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Supervisor Agent 상태 점검
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            # 워크플로우 디렉토리 확인
            workflow_dir_exists = self.workflow_dir.exists()
            workflow_dir_writable = self.workflow_dir.is_dir() and os.access(self.workflow_dir, os.W_OK)
            
            # 활성 워크플로우 통계
            active_workflows = len(self.active_workflows)
            workflow_statuses = {}
            for workflow in self.active_workflows.values():
                status = workflow.status
                workflow_statuses[status] = workflow_statuses.get(status, 0) + 1
            
            return {
                "status": "healthy",
                "workflow_dir": str(self.workflow_dir),
                "workflow_dir_exists": workflow_dir_exists,
                "workflow_dir_writable": workflow_dir_writable,
                "active_workflows": active_workflows,
                "workflow_statuses": workflow_statuses,
                "registered_agents": list(self.agent_registry.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 
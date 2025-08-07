"""
비동기 스케줄러 유틸리티

PRD 요구사항에 따른 주기적 스냅샷 저장 및 워크플로우 단계 완료 시 자동 저장
"""

import asyncio
import logging
from typing import Callable, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from server.schemas.base import WorkflowState, WorkflowStage

logger = logging.getLogger(__name__)


@dataclass
class SchedulerTask:
    """스케줄러 작업 정의"""
    name: str
    interval: float  # 초
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.next_run is None:
            self.next_run = datetime.utcnow() + timedelta(seconds=self.interval)


class PeriodicScheduler:
    """
    주기적 작업 스케줄러
    
    PRD 요구사항:
    - 60초 주기 스냅샷 저장
    - 워크플로우 단계 완료 시 자동 저장
    """
    
    def __init__(self, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        self.tasks: Dict[str, SchedulerTask] = {}
        self.running = False
        self._task_handle: Optional[asyncio.Task] = None
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.stage_watchers: Set[str] = set()
        
    def add_task(
        self,
        name: str,
        func: Callable,
        interval: float,
        args: tuple = (),
        kwargs: dict = None,
        enabled: bool = True
    ):
        """스케줄러 작업 추가"""
        self.tasks[name] = SchedulerTask(
            name=name,
            func=func,
            interval=interval,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled
        )
        logger.info(f"스케줄러 작업 추가: {name} ({interval}초 간격)")
    
    def remove_task(self, name: str):
        """스케줄러 작업 제거"""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"스케줄러 작업 제거: {name}")
    
    def enable_task(self, name: str):
        """작업 활성화"""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"스케줄러 작업 활성화: {name}")
    
    def disable_task(self, name: str):
        """작업 비활성화"""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"스케줄러 작업 비활성화: {name}")
    
    async def _run_task(self, task: SchedulerTask):
        """개별 작업 실행"""
        try:
            task.last_run = datetime.utcnow()
            
            if asyncio.iscoroutinefunction(task.func):
                await task.func(*task.args, **task.kwargs)
            else:
                # 동기 함수를 executor에서 실행
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, task.func, *task.args)
                
            task.next_run = datetime.utcnow() + timedelta(seconds=task.interval)
            logger.debug(f"작업 실행 완료: {task.name}")
            
        except Exception as e:
            logger.error(f"작업 실행 실패 {task.name}: {e}")
            # 오류가 발생해도 다음 실행 시간은 설정
            task.next_run = datetime.utcnow() + timedelta(seconds=task.interval)
    
    async def _scheduler_loop(self):
        """메인 스케줄러 루프"""
        logger.info("스케줄러 시작")
        
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # 실행할 작업 찾기
                for task in self.tasks.values():
                    if (task.enabled and 
                        task.next_run <= current_time):
                        await self._run_task(task)
                
                # 잠시 대기 (CPU 사용률 최적화)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"스케줄러 루프 오류: {e}")
                await asyncio.sleep(5)  # 오류 시 조금 더 대기
        
        logger.info("스케줄러 종료")
    
    async def start(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        self.running = True
        self._task_handle = asyncio.create_task(self._scheduler_loop())
        
        # 기본 작업들 등록
        self._register_default_tasks()
        
        logger.info("스케줄러 시작됨")
    
    async def stop(self):
        """스케줄러 중지"""
        if not self.running:
            return
        
        self.running = False
        
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass
        
        logger.info("스케줄러 중지됨")
    
    def _register_default_tasks(self):
        """기본 스케줄러 작업 등록"""
        # PRD 요구사항: 60초 주기 스냅샷 저장
        self.add_task(
            name="periodic_snapshot",
            func=self._periodic_snapshot_task,
            interval=60.0,  # 60초
            enabled=True
        )
        
        # 5분마다 만료된 체크포인트 정리
        self.add_task(
            name="cleanup_expired",
            func=self._cleanup_expired_task,
            interval=300.0,  # 5분
            enabled=True
        )
    
    async def _periodic_snapshot_task(self):
        """주기적 스냅샷 저장 작업"""
        if not self.active_workflows:
            logger.debug("활성 워크플로우가 없어 스냅샷을 건너뜀")
            return
        
        saved_count = 0
        for workflow_id, workflow_state in self.active_workflows.items():
            try:
                key = await self.snapshot_manager.save_workflow_state_async(
                    workflow_state, 
                    checkpoint_type="periodic"
                )
                saved_count += 1
                logger.debug(f"주기적 스냅샷 저장: {workflow_id} -> {key}")
                
            except Exception as e:
                logger.error(f"워크플로우 {workflow_id} 스냅샷 저장 실패: {e}")
        
        if saved_count > 0:
            logger.info(f"주기적 스냅샷 저장 완료: {saved_count}개 워크플로우")
    
    def _cleanup_expired_task(self):
        """만료된 체크포인트 정리 작업"""
        try:
            deleted_count = self.snapshot_manager.cleanup_expired_checkpoints()
            if deleted_count > 0:
                logger.info(f"만료된 체크포인트 정리: {deleted_count}개")
        except Exception as e:
            logger.error(f"체크포인트 정리 실패: {e}")
    
    def register_workflow(self, workflow_state: WorkflowState):
        """워크플로우 등록 (스냅샷 대상에 추가)"""
        self.active_workflows[workflow_state.workflow_id] = workflow_state
        self.stage_watchers.add(workflow_state.workflow_id)
        logger.info(f"워크플로우 등록: {workflow_state.workflow_id}")
    
    def unregister_workflow(self, workflow_id: str):
        """워크플로우 등록 해제"""
        self.active_workflows.pop(workflow_id, None)
        self.stage_watchers.discard(workflow_id)
        logger.info(f"워크플로우 등록 해제: {workflow_id}")
    
    def update_workflow_state(self, workflow_state: WorkflowState):
        """워크플로우 상태 업데이트"""
        old_state = self.active_workflows.get(workflow_state.workflow_id)
        self.active_workflows[workflow_state.workflow_id] = workflow_state
        
        # 단계 완료 시 즉시 스냅샷 저장
        if old_state and self._stage_completed(old_state, workflow_state):
            asyncio.create_task(self._save_stage_completion_snapshot(workflow_state))
    
    def _stage_completed(self, old_state: WorkflowState, new_state: WorkflowState) -> bool:
        """워크플로우 단계 완료 여부 확인"""
        stage_fields = [
            "research_completed",
            "extraction_completed", 
            "retrieval_completed",
            "wiki_completed",
            "graph_completed",
            "feedback_completed"
        ]
        
        for field in stage_fields:
            old_value = getattr(old_state, field, False)
            new_value = getattr(new_state, field, False)
            if not old_value and new_value:  # 새로 완료된 단계 발견
                return True
        return False
    
    async def _save_stage_completion_snapshot(self, workflow_state: WorkflowState):
        """단계 완료 시 스냅샷 저장"""
        try:
            key = await self.snapshot_manager.save_workflow_state_async(
                workflow_state,
                checkpoint_type="stage_completion"
            )
            logger.info(f"단계 완료 스냅샷 저장: {workflow_state.workflow_id} -> {key}")
            
        except Exception as e:
            logger.error(f"단계 완료 스냅샷 저장 실패: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 정보"""
        return {
            "running": self.running,
            "active_workflows": len(self.active_workflows),
            "registered_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "tasks": {
                name: {
                    "enabled": task.enabled,
                    "interval": task.interval,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None
                }
                for name, task in self.tasks.items()
            }
        }


class WorkflowStateManager:
    """
    워크플로우 상태 관리자
    
    스케줄러와 스냅샷 매니저를 통합한 고수준 인터페이스
    """
    
    def __init__(self, snapshot_manager):
        self.snapshot_manager = snapshot_manager
        self.scheduler = PeriodicScheduler(snapshot_manager)
        
    async def start(self):
        """서비스 시작"""
        await self.scheduler.start()
        logger.info("워크플로우 상태 관리자 시작")
    
    async def stop(self):
        """서비스 중지"""
        await self.scheduler.stop()
        logger.info("워크플로우 상태 관리자 중지")
    
    def create_workflow(self, keyword: str, trace_id: str) -> WorkflowState:
        """새 워크플로우 생성"""
        workflow_state = WorkflowState(
            trace_id=trace_id,
            keyword=keyword
        )
        
        # 스케줄러에 등록
        self.scheduler.register_workflow(workflow_state)
        
        # 초기 스냅샷 저장
        asyncio.create_task(
            self.snapshot_manager.save_workflow_state_async(
                workflow_state, 
                checkpoint_type="initial"
            )
        )
        
        logger.info(f"새 워크플로우 생성: {workflow_state.workflow_id}")
        return workflow_state
    
    def update_workflow(self, workflow_state: WorkflowState):
        """워크플로우 상태 업데이트"""
        self.scheduler.update_workflow_state(workflow_state)
    
    def complete_workflow(self, workflow_id: str):
        """워크플로우 완료"""
        workflow_state = self.scheduler.active_workflows.get(workflow_id)
        if workflow_state:
            workflow_state.completed_at = datetime.utcnow()
            workflow_state.total_processing_time = (
                (workflow_state.completed_at - workflow_state.created_at).total_seconds()
            )
            
            # 최종 스냅샷 저장
            asyncio.create_task(
                self.snapshot_manager.save_workflow_state_async(
                    workflow_state,
                    checkpoint_type="final"
                )
            )
            
            # 스케줄러에서 제거
            self.scheduler.unregister_workflow(workflow_id)
            
            logger.info(f"워크플로우 완료: {workflow_id}")
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회"""
        # 먼저 메모리에서 확인
        if workflow_id in self.scheduler.active_workflows:
            return self.scheduler.active_workflows[workflow_id]
        
        # Redis에서 조회
        return await self.snapshot_manager.get_workflow_state_async(workflow_id)
    
    def get_manager_status(self) -> Dict[str, Any]:
        """관리자 상태 정보"""
        return {
            "scheduler": self.scheduler.get_status(),
            "snapshot_manager": {
                "redis_connected": self.snapshot_manager.redis_manager.test_connection()
            }
        }
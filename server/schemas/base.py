"""
기본 메시지 스키마 및 상태 관리 스키마

PRD 요구사항에 따른 공통 메시지 헤더와 상태 스키마 정의
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, UTC
from enum import Enum
import uuid

from pydantic import BaseModel, Field, field_validator


class AgentType(str, Enum):
    """에이전트 타입 열거형"""
    RESEARCH = "research"
    EXTRACTOR = "extractor" 
    RETRIEVER = "retriever"
    WIKI = "wiki"
    GRAPHVIZ = "graphviz"
    SUPERVISOR = "supervisor"
    FEEDBACK = "feedback"


class MessageStatus(str, Enum):
    """메시지 상태 열거형"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStage(str, Enum):
    """워크플로우 단계 열거형"""
    RESEARCH = "research"
    EXTRACTION = "extraction"  
    RETRIEVAL = "retrieval"
    WIKI_GENERATION = "wiki_generation"
    GRAPH_VISUALIZATION = "graph_visualization"
    FEEDBACK_PROCESSING = "feedback_processing"
    COMPLETED = "completed"


class CheckpointType(str, Enum):
    """체크포인트 타입 열거형"""
    PERIODIC = "periodic"                # 60초 주기 자동 저장
    STAGE_COMPLETION = "stage_completion" # 워크플로우 단계 완료 시 저장
    MANUAL = "manual"                    # 수동 저장
    ERROR_RECOVERY = "error_recovery"    # 오류 복구 시 저장


class MessageHeader(BaseModel):
    """
    공통 메시지 헤더
    
    PRD 요구사항: msg_id, agent, ts, trace_id, version
    """
    msg_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="메시지 고유 식별자"
    )
    agent: AgentType = Field(
        description="메시지를 생성한 에이전트 타입"
    )
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description="메시지 생성 타임스탬프 (UTC)"
    )
    trace_id: str = Field(
        description="워크플로우 추적을 위한 고유 ID"
    )
    version: str = Field(
        default="1.0.0",
        description="메시지 스키마 버전"
    )
    
    @field_validator('trace_id')
    @classmethod
    def validate_trace_id(cls, v):
        """trace_id 형식 검증"""
        if not v or len(v) < 8:
            raise ValueError("trace_id는 최소 8자 이상이어야 합니다")
        return v


class MessageBase(BaseModel):
    """
    기본 메시지 구조
    
    모든 에이전트 메시지의 기본 클래스
    """
    header: MessageHeader = Field(description="메시지 헤더")
    status: MessageStatus = Field(
        default=MessageStatus.PENDING,
        description="메시지 처리 상태"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="메시지 페이로드 데이터"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="오류 발생 시 오류 메시지"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="메시지 생성 시간"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="메시지 최종 수정 시간"
    )
    
    def mark_processing(self):
        """메시지를 처리 중 상태로 변경"""
        self.status = MessageStatus.PROCESSING
        self.updated_at = datetime.now(UTC)
    
    def mark_completed(self, payload: Optional[Dict[str, Any]] = None):
        """메시지를 완료 상태로 변경"""
        self.status = MessageStatus.COMPLETED
        self.updated_at = datetime.now(UTC)
        if payload:
            self.payload.update(payload)
    
    def mark_failed(self, error_message: str):
        """메시지를 실패 상태로 변경"""
        self.status = MessageStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now(UTC)


class WorkflowState(BaseModel):
    """
    워크플로우 상태 관리
    
    Redis-JSON Snapshot에 저장될 전체 워크플로우 상태
    """
    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="워크플로우 고유 식별자"
    )
    trace_id: str = Field(description="추적 ID")
    current_stage: WorkflowStage = Field(
        default=WorkflowStage.RESEARCH,
        description="현재 워크플로우 단계"
    )
    keyword: str = Field(description="초기 입력 키워드")
    
    # 각 단계별 상태
    research_completed: bool = Field(default=False)
    extraction_completed: bool = Field(default=False)
    retrieval_completed: bool = Field(default=False)
    wiki_completed: bool = Field(default=False)
    graph_completed: bool = Field(default=False)
    feedback_completed: bool = Field(default=False)
    
    # 각 단계별 결과 데이터
    research_results: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_relations: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: List[str] = Field(default_factory=list)
    wiki_content: Optional[str] = Field(default=None)
    graph_data: Optional[Dict[str, Any]] = Field(default=None)
    feedback_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 메타데이터
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = Field(default=None)
    total_processing_time: Optional[float] = Field(default=None)
    
    def advance_to_stage(self, stage: WorkflowStage):
        """다음 단계로 진행"""
        self.current_stage = stage
        self.updated_at = datetime.utcnow()
    
    def mark_stage_completed(self, stage: WorkflowStage):
        """특정 단계를 완료로 표시"""
        stage_mapping = {
            WorkflowStage.RESEARCH: "research_completed",
            WorkflowStage.EXTRACTION: "extraction_completed", 
            WorkflowStage.RETRIEVAL: "retrieval_completed",
            WorkflowStage.WIKI_GENERATION: "wiki_completed",
            WorkflowStage.GRAPH_VISUALIZATION: "graph_completed",
            WorkflowStage.FEEDBACK_PROCESSING: "feedback_completed"
        }
        
        if stage in stage_mapping:
            setattr(self, stage_mapping[stage], True)
            self.updated_at = datetime.utcnow()
    
    def is_completed(self) -> bool:
        """전체 워크플로우 완료 여부 확인"""
        return (
            self.research_completed and
            self.extraction_completed and
            self.retrieval_completed and
            self.wiki_completed and
            self.graph_completed
        )
    
    def get_completion_percentage(self) -> float:
        """완료 비율 계산"""
        completed_stages = sum([
            self.research_completed,
            self.extraction_completed, 
            self.retrieval_completed,
            self.wiki_completed,
            self.graph_completed
        ])
        return (completed_stages / 5) * 100


class CheckpointData(BaseModel):
    """
    체크포인트 데이터
    
    Redis-JSON에 저장될 체크포인트 정보
    """
    checkpoint_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="체크포인트 고유 식별자"
    )
    workflow_id: str = Field(description="연관된 워크플로우 ID")
    checkpoint_type: CheckpointType = Field(
        description="체크포인트 타입"
    )
    state_snapshot: WorkflowState = Field(description="상태 스냅샷")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="체크포인트 생성 시각",
        alias="created_at"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="추가 메타데이터"
    )
    retention_until: Optional[datetime] = Field(
        default=None,
        description="체크포인트 보관 기한"
    )


class SystemStatus(BaseModel):
    """
    시스템 전체 상태
    
    모니터링 및 헬스체크용
    """
    system_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="시스템 인스턴스 ID"
    )
    status: str = Field(description="시스템 상태 (healthy, degraded, unhealthy)")
    active_workflows: int = Field(default=0, description="활성 워크플로우 수")
    completed_workflows: int = Field(default=0, description="완료된 워크플로우 수")
    failed_workflows: int = Field(default=0, description="실패한 워크플로우 수")
    
    # 각 에이전트 상태
    agents_status: Dict[AgentType, bool] = Field(
        default_factory=dict,
        description="각 에이전트의 활성 상태"
    )
    
    # 외부 서비스 상태
    redis_connected: bool = Field(default=False)
    rdflib_connected: bool = Field(default=False)
    openai_available: bool = Field(default=False)
    
    last_health_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uptime_seconds: Optional[float] = Field(default=None)
    
    def is_healthy(self) -> bool:
        """시스템 건강 상태 확인"""
        return (
            self.status == "healthy" and
            self.redis_connected and
            self.rdflib_connected and
            self.openai_available
        )
"""
AI Knowledge Graph System - Schema Package

이 패키지는 시스템 전반에서 사용되는 Pydantic 스키마를 정의합니다:
- 공통 메시지 헤더 및 상태 스키마
- 7개 에이전트의 Input/Output 스키마  
- 워크플로우 및 체크포인트 스키마
"""

from .base import (
    AgentType,
    MessageStatus,
    WorkflowStage,
    CheckpointType,
    MessageHeader,
    MessageBase,
    WorkflowState,
    CheckpointData,
    SystemStatus
)

from .agents import (
    # Research Agent
    ResearchIn,
    ResearchOut,
    
    # Extractor Agent  
    ExtractorIn,
    ExtractorOut,
    Entity,
    Relation,
    
    # Retriever Agent
    RetrieverIn, 
    RetrieverOut,
    
    # Wiki Agent
    WikiIn,
    WikiOut,
    
    # GraphViz Agent
    GraphVizIn,
    GraphVizOut,
    
    # Supervisor Agent
    SupervisorIn,
    SupervisorOut,
    
    # Feedback Agent
    FeedbackIn,
    FeedbackOut
)

__all__ = [
    # Base schemas
    "AgentType",
    "MessageStatus",
    "WorkflowStage", 
    "CheckpointType",
    "MessageHeader",
    "MessageBase", 
    "WorkflowState",
    "CheckpointData",
    "SystemStatus",
    
    # Agent schemas
    "ResearchIn",
    "ResearchOut",
    "ExtractorIn", 
    "ExtractorOut",
    "Entity",
    "Relation",
    "RetrieverIn",
    "RetrieverOut", 
    "WikiIn",
    "WikiOut",
    "GraphVizIn",
    "GraphVizOut",
    "SupervisorIn",
    "SupervisorOut",
    "FeedbackIn", 
    "FeedbackOut"
]
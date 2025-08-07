"""
Checkpointer API 라우터

PRD 요구사항에 따른 상태 스냅샷 저장/조회 REST API 제공
- 체크포인트 저장/조회/삭제
- Redis-JSON 연동을 통한 상태 관리
- 입력 검증 및 예외 처리
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field
import logging

from src.core.schemas.base import CheckpointData, WorkflowState, CheckpointType
from src.core.schemas.agents import *  # 모든 에이전트 스키마 import
from src.core.utils.redis_manager import SnapshotManager, RedisConfig, RedisManager
from src.core.utils.config import settings

logger = logging.getLogger(__name__)

# 라우터 초기화
router = APIRouter(
    prefix="/api/v1/checkpoints",
    tags=["checkpoints"],
    responses={
        404: {"description": "Checkpoint not found"},
        500: {"description": "Internal server error"}
    }
)

# 전역 Redis 매니저 및 스냅샷 매니저
redis_manager: Optional[RedisManager] = None
snapshot_manager: Optional[SnapshotManager] = None


async def get_snapshot_manager() -> SnapshotManager:
    """스냅샷 매니저 의존성"""
    global redis_manager, snapshot_manager
    
    if snapshot_manager is None:
        try:
            redis_config = settings.get_redis_config()
            redis_manager = RedisManager(redis_config)
            snapshot_manager = SnapshotManager(redis_manager)
            logger.info("SnapshotManager 초기화 완료")
        except Exception as e:
            logger.error(f"SnapshotManager 초기화 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="Redis 연결 실패"
            )
    
    return snapshot_manager


# =============================================================================
# Request/Response 모델
# =============================================================================

class SaveCheckpointRequest(BaseModel):
    """체크포인트 저장 요청"""
    workflow_id: str = Field(description="워크플로우 ID")
    checkpoint_type: CheckpointType = Field(description="체크포인트 타입")
    state_snapshot: WorkflowState = Field(description="워크플로우 상태 스냅샷")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="추가 메타데이터"
    )


class CheckpointResponse(BaseModel):
    """체크포인트 응답"""
    checkpoint_id: str
    workflow_id: str
    checkpoint_type: str
    timestamp: datetime
    metadata: Dict[str, Any]
    state_snapshot: WorkflowState


class CheckpointListResponse(BaseModel):
    """체크포인트 목록 응답"""
    checkpoints: List[CheckpointResponse]
    total: int
    page: int
    page_size: int


class SaveCheckpointResponse(BaseModel):
    """체크포인트 저장 응답"""
    checkpoint_id: str
    message: str
    timestamp: datetime


# =============================================================================
# API 엔드포인트
# =============================================================================

@router.post("/", response_model=SaveCheckpointResponse)
async def save_checkpoint(
    request: SaveCheckpointRequest,
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    체크포인트 저장
    
    워크플로우 상태를 Redis-JSON에 스냅샷으로 저장합니다.
    """
    try:
        # CheckpointData 객체 생성
        checkpoint_data = CheckpointData(
            workflow_id=request.workflow_id,
            checkpoint_type=request.checkpoint_type,
            state_snapshot=request.state_snapshot,
            metadata=request.metadata
        )
        
        # Redis에 저장
        checkpoint_id = await snapshot_manager.save_checkpoint(checkpoint_data)
        
        logger.info(f"체크포인트 저장 성공: {checkpoint_id}")
        
        return SaveCheckpointResponse(
            checkpoint_id=checkpoint_id,
            message="체크포인트가 성공적으로 저장되었습니다",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"체크포인트 저장 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"체크포인트 저장 중 오류 발생: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=List[CheckpointResponse])
async def get_checkpoints(
    workflow_id: str = Path(description="워크플로우 ID"),
    checkpoint_type: Optional[str] = Query(None, description="체크포인트 타입 필터"),
    limit: int = Query(10, ge=1, le=100, description="최대 조회 개수"),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    특정 워크플로우의 체크포인트 목록 조회
    
    워크플로우 ID로 저장된 모든 체크포인트를 조회합니다.
    """
    try:
        checkpoints = await snapshot_manager.get_checkpoints_by_workflow(
            workflow_id, 
            checkpoint_type=checkpoint_type,
            limit=limit
        )
        
        if not checkpoints:
            return []
        
        # CheckpointResponse 형태로 변환
        response_data = []
        for checkpoint in checkpoints:
            response_data.append(CheckpointResponse(
                checkpoint_id=checkpoint.checkpoint_id,
                workflow_id=checkpoint.workflow_id,
                checkpoint_type=checkpoint.checkpoint_type,
                timestamp=checkpoint.timestamp,
                metadata=checkpoint.metadata,
                state_snapshot=checkpoint.state_snapshot
            ))
        
        logger.info(f"체크포인트 조회 성공: {workflow_id}, {len(response_data)}개")
        return response_data
        
    except Exception as e:
        logger.error(f"체크포인트 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"체크포인트 조회 중 오류 발생: {str(e)}"
        )


@router.get("/{workflow_id}/latest", response_model=CheckpointResponse)
async def get_latest_checkpoint(
    workflow_id: str = Path(description="워크플로우 ID"),
    checkpoint_type: Optional[str] = Query(None, description="체크포인트 타입 필터"),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    최신 체크포인트 조회
    
    특정 워크플로우의 가장 최근 체크포인트를 조회합니다.
    """
    try:
        checkpoint = await snapshot_manager.get_latest_checkpoint(
            workflow_id,
            checkpoint_type=checkpoint_type
        )
        
        if not checkpoint:
            raise HTTPException(
                status_code=404,
                detail=f"워크플로우 {workflow_id}의 체크포인트를 찾을 수 없습니다"
            )
        
        logger.info(f"최신 체크포인트 조회 성공: {workflow_id}")
        
        return CheckpointResponse(
            checkpoint_id=checkpoint.checkpoint_id,
            workflow_id=checkpoint.workflow_id,
            checkpoint_type=checkpoint.checkpoint_type,
            timestamp=checkpoint.timestamp,
            metadata=checkpoint.metadata,
            state_snapshot=checkpoint.state_snapshot
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최신 체크포인트 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"최신 체크포인트 조회 중 오류 발생: {str(e)}"
        )


@router.delete("/{workflow_id}")
async def delete_checkpoints(
    workflow_id: str = Path(description="워크플로우 ID"),
    checkpoint_type: Optional[str] = Query(None, description="특정 타입만 삭제"),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    체크포인트 삭제
    
    특정 워크플로우의 체크포인트를 삭제합니다.
    """
    try:
        deleted_count = await snapshot_manager.delete_checkpoints(
            workflow_id,
            checkpoint_type=checkpoint_type
        )
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"삭제할 체크포인트를 찾을 수 없습니다"
            )
        
        logger.info(f"체크포인트 삭제 성공: {workflow_id}, {deleted_count}개")
        
        return {
            "message": f"{deleted_count}개 체크포인트가 삭제되었습니다",
            "workflow_id": workflow_id,
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"체크포인트 삭제 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"체크포인트 삭제 중 오류 발생: {str(e)}"
        )


@router.get("/", response_model=CheckpointListResponse)
async def list_all_checkpoints(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    checkpoint_type: Optional[str] = Query(None, description="체크포인트 타입 필터"),
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    전체 체크포인트 목록 조회 (페이지네이션)
    
    시스템의 모든 체크포인트를 페이지네이션으로 조회합니다.
    """
    try:
        checkpoints, total = await snapshot_manager.list_all_checkpoints(
            page=page,
            page_size=page_size,
            checkpoint_type=checkpoint_type
        )
        
        # CheckpointResponse 형태로 변환
        response_data = []
        for checkpoint in checkpoints:
            response_data.append(CheckpointResponse(
                checkpoint_id=checkpoint.checkpoint_id,
                workflow_id=checkpoint.workflow_id,
                checkpoint_type=checkpoint.checkpoint_type,
                timestamp=checkpoint.timestamp,
                metadata=checkpoint.metadata,
                state_snapshot=checkpoint.state_snapshot
            ))
        
        logger.info(f"전체 체크포인트 목록 조회 성공: {len(response_data)}/{total}")
        
        return CheckpointListResponse(
            checkpoints=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"전체 체크포인트 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"체크포인트 목록 조회 중 오류 발생: {str(e)}"
        )


# =============================================================================
# 헬스체크 및 상태 조회
# =============================================================================

@router.get("/health/status")
async def health_check(
    snapshot_manager: SnapshotManager = Depends(get_snapshot_manager)
):
    """
    Checkpointer API 헬스체크
    
    Redis 연결 상태 및 시스템 상태를 확인합니다.
    """
    try:
        # Redis 연결 테스트
        is_healthy = await snapshot_manager.health_check()
        
        if not is_healthy:
            raise HTTPException(
                status_code=503,
                detail="Redis 연결 상태가 불안정합니다"
            )
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "redis_connection": "active",
            "message": "Checkpointer API가 정상적으로 작동 중입니다"
        }
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"시스템 상태 확인 중 오류 발생: {str(e)}"
        )
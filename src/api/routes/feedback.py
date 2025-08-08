"""
Feedback API 라우터

피드백 제출, 조회, 통계 API 엔드포인트
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.agents.feedback import FeedbackAgent, FeedbackItem
from src.core.schemas.agents import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# 피드백 에이전트 인스턴스
feedback_agent = FeedbackAgent()


class FeedbackSubmitRequest(BaseModel):
    """피드백 제출 요청"""
    workflow_id: str
    user_id: str
    feedback_type: str = "general"
    content: str
    rating: Optional[int] = None


class FeedbackResponse(BaseModel):
    """피드백 응답"""
    feedback_id: str
    workflow_id: str
    user_id: str
    feedback_type: str
    content: str
    rating: Optional[int]
    status: str
    created_at: str
    processed_at: Optional[str]


class FeedbackListResponse(BaseModel):
    """피드백 목록 응답"""
    feedbacks: List[FeedbackResponse]
    total: int


class FeedbackStatisticsResponse(BaseModel):
    """피드백 통계 응답"""
    total_feedback: int
    status_counts: dict
    rating_counts: dict
    recent_feedback: int
    generated_at: str


@router.post("/submit", response_model=FeedbackOut)
async def submit_feedback(request: FeedbackSubmitRequest):
    """피드백 제출"""
    try:
        # FeedbackIn 스키마로 변환
        feedback_input = FeedbackIn(
            node_id=request.workflow_id,  # node_id를 workflow_id로 사용
            feedback=request.content,
            feedback_type=request.feedback_type,
            user_id=request.user_id,
            confidence=1.0
        )
        
        # 피드백 처리
        result = feedback_agent.process(feedback_input)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 제출 실패: {str(e)}")


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(feedback_id: str):
    """특정 피드백 조회"""
    try:
        feedback = feedback_agent.get_feedback(feedback_id)
        
        if not feedback:
            raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다")
        
        return FeedbackResponse(
            feedback_id=feedback.id,
            workflow_id=feedback.workflow_id,
            user_id=feedback.user_id,
            feedback_type=feedback.feedback_type,
            content=feedback.content,
            rating=feedback.rating,
            status=feedback.status,
            created_at=feedback.created_at.isoformat(),
            processed_at=feedback.processed_at.isoformat() if feedback.processed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 조회 실패: {str(e)}")


@router.get("/", response_model=FeedbackListResponse)
async def list_feedback(
    workflow_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """피드백 목록 조회"""
    try:
        feedbacks = feedback_agent.list_feedback(
            workflow_id=workflow_id,
            user_id=user_id,
            status=status,
            limit=limit
        )
        
        feedback_responses = [
            FeedbackResponse(
                feedback_id=feedback.id,
                workflow_id=feedback.workflow_id,
                user_id=feedback.user_id,
                feedback_type=feedback.feedback_type,
                content=feedback.content,
                rating=feedback.rating,
                status=feedback.status,
                created_at=feedback.created_at.isoformat(),
                processed_at=feedback.processed_at.isoformat() if feedback.processed_at else None
            )
            for feedback in feedbacks
        ]
        
        return FeedbackListResponse(
            feedbacks=feedback_responses,
            total=len(feedback_responses)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 목록 조회 실패: {str(e)}")


@router.put("/{feedback_id}/status")
async def update_feedback_status(feedback_id: str, status: str):
    """피드백 상태 업데이트"""
    try:
        success = feedback_agent.update_feedback_status(feedback_id, status)
        
        if not success:
            raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다")
        
        return {"message": f"피드백 상태가 {status}로 업데이트되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 상태 업데이트 실패: {str(e)}")


@router.get("/statistics", response_model=FeedbackStatisticsResponse)
async def get_feedback_statistics():
    """피드백 통계 조회"""
    try:
        stats = feedback_agent.get_feedback_statistics()
        
        return FeedbackStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 통계 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """피드백 서비스 상태 확인"""
    try:
        health_info = feedback_agent.health_check()
        return health_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")
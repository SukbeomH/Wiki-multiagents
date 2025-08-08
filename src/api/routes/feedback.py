"""
Feedback API 라우터

피드백 제출, 조회, 통계 API 엔드포인트
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.agents.feedback import FeedbackAgent, FeedbackItem
from src.core.schemas.agents import FeedbackIn, FeedbackOut
from src.core.utils.kg_manager import RDFLibKnowledgeGraphManager

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# 피드백 에이전트 및 KG 매니저 인스턴스
feedback_agent = FeedbackAgent()
kg_manager = RDFLibKnowledgeGraphManager()


class FeedbackSubmitRequest(BaseModel):
    """피드백 제출 요청"""
    workflow_id: str
    user_id: str
    feedback_type: str = "general"
    content: str
    rating: Optional[int] = None
    kg_updates: Optional[Dict[str, Any]] = None  # KG 업데이트 정보


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
    kg_updates_applied: Optional[bool] = None  # KG 업데이트 적용 여부


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
    """피드백 제출 및 KG 업데이트"""
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
        
        # KG 업데이트 처리
        kg_updates_applied = False
        if request.kg_updates:
            try:
                kg_updates_applied = await _apply_kg_updates(request.kg_updates)
            except Exception as kg_error:
                # KG 업데이트 실패는 피드백 처리에 영향을 주지 않도록 함
                print(f"KG 업데이트 실패 (피드백은 성공): {kg_error}")
        
        # 결과에 KG 업데이트 상태 추가
        if hasattr(result, 'dict'):
            result_dict = result.dict()
            result_dict['kg_updates_applied'] = kg_updates_applied
            return result_dict
        else:
            return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 제출 실패: {str(e)}")


async def _apply_kg_updates(kg_updates: Dict[str, Any]) -> bool:
    """KG 업데이트 적용"""
    try:
        # 엔티티 업데이트
        if 'entities' in kg_updates:
            for entity_id, properties in kg_updates['entities'].items():
                success = kg_manager.update_entity(entity_id, properties)
                if not success:
                    print(f"엔티티 업데이트 실패: {entity_id}")
                    return False
        
        # 관계 업데이트
        if 'relations' in kg_updates:
            for relation_id, properties in kg_updates['relations'].items():
                success = kg_manager.update_relation(relation_id, properties)
                if not success:
                    print(f"관계 업데이트 실패: {relation_id}")
                    return False
        
        # 관계 엔드포인트 업데이트
        if 'relation_endpoints' in kg_updates:
            for relation_id, endpoint_data in kg_updates['relation_endpoints'].items():
                success = kg_manager.update_relation_endpoints(
                    relation_id,
                    new_source_id=endpoint_data.get('new_source_id'),
                    new_target_id=endpoint_data.get('new_target_id')
                )
                if not success:
                    print(f"관계 엔드포인트 업데이트 실패: {relation_id}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"KG 업데이트 처리 중 오류: {e}")
        return False





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
        
        # 실제 반환값과 스키마 매칭
        return FeedbackStatisticsResponse(
            total_feedback=stats.get("total_feedback", 0),
            status_counts=stats.get("status_counts", {}),
            rating_counts=stats.get("rating_counts", {}),
            recent_feedback=stats.get("recent_feedback", 0),
            generated_at=stats.get("generated_at", "")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 통계 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """피드백 서비스 상태 확인"""
    try:
        health_info = feedback_agent.health_check()
        # health_info는 dict이므로 그대로 반환 (스키마 검증 없음)
        return health_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.get("/kg/status")
async def get_kg_status():
    """Knowledge Graph 상태 확인"""
    try:
        # KG 통계 정보 반환
        stats = {
            "total_entities": len(kg_manager.query_entities()),
            "total_relations": len(kg_manager.query_relations()),
            "graph_size": len(kg_manager.graph),
            "status": "active"
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KG 상태 확인 실패: {str(e)}")


@router.post("/kg/update")
async def update_kg_directly(updates: Dict[str, Any]):
    """직접 KG 업데이트 (테스트용)"""
    try:
        success = await _apply_kg_updates(updates)
        return {"success": success, "message": "KG 업데이트 완료" if success else "KG 업데이트 실패"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KG 업데이트 실패: {str(e)}")


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
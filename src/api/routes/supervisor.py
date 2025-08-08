"""
Supervisor API Router

지식 그래프 생성 워크플로우를 처리하는 API 엔드포인트
"""

import time
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.supervisor.agent import SupervisorAgent
from src.core.schemas.agents import SupervisorIn, SupervisorOut

# API 라우터 설정
router = APIRouter(
    prefix="/api/v1/supervisor",
    tags=["supervisor"],
    responses={404: {"description": "Not found"}},
)


class SupervisorRequest(BaseModel):
    """Supervisor 워크플로우 요청 모델"""
    trace_id: str
    user_id: str
    request: Dict[str, Any]


class SupervisorResponse(BaseModel):
    """Supervisor 워크플로우 응답 모델"""
    status: str = "success"
    trace_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/process")
async def process_knowledge_workflow(request: SupervisorRequest):
    """
    지식 그래프 생성 워크플로우 실행
    
    Args:
        request: 워크플로우 요청 데이터
        
    Returns:
        워크플로우 실행 결과
    """
    try:
        # 요청 데이터 추출
        keyword = request.request.get("keyword", "")
        top_k = request.request.get("top_k", 10)
        extraction_mode = request.request.get("extraction_mode", "comprehensive")
        
        if not keyword.strip():
            raise HTTPException(status_code=400, detail="키워드가 필요합니다.")
        
        # Supervisor Agent 초기화
        supervisor_agent = SupervisorAgent()
        
        # 워크플로우 입력 데이터 생성
        workflow_input = SupervisorIn(
            trace_id=request.trace_id,
            user_id=request.user_id,
            request={
                "keyword": keyword,
                "top_k": top_k,
                "extraction_mode": extraction_mode
            }
        )
        
        # 워크플로우 실행
        print(f"🔍 지식 그래프 워크플로우 시작: {keyword}")
        start_time = time.time()
        
        result = supervisor_agent.process(workflow_input)
        
        execution_time = time.time() - start_time
        print(f"✅ 워크플로우 완료: {execution_time:.2f}초")
        
        # 응답 데이터 구성
        response_data = {
            "graph_data": result.graph_data if hasattr(result, 'graph_data') else None,
            "wiki_content": result.wiki_content if hasattr(result, 'wiki_content') else None,
            "execution_time": execution_time,
            "keyword": keyword,
            "status": "completed"
        }
        
        return SupervisorResponse(
            status="success",
            trace_id=request.trace_id,
            result=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 워크플로우 실행 오류: {str(e)}")
        return SupervisorResponse(
            status="error",
            trace_id=request.trace_id,
            error=str(e)
        )


@router.get("/health")
async def supervisor_health():
    """Supervisor 서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": "supervisor",
        "timestamp": time.time()
    }


@router.get("/status")
async def supervisor_status():
    """Supervisor 서비스 상태 확인"""
    return {
        "status": "running",
        "service": "supervisor",
        "version": "1.0.0",
        "timestamp": time.time()
    } 
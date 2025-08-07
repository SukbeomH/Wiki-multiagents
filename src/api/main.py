"""
FastAPI 메인 애플리케이션

모든 API 라우터를 통합하는 메인 애플리케이션
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes import (
    checkpoints_router,
    retriever_router,
    workflow_router,
    history_router
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="AI Bootcamp Final API",
    description="멀티-에이전트 기반 지식 그래프 워크플로우 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(checkpoints_router)
app.include_router(retriever_router)
app.include_router(workflow_router)
app.include_router(history_router)

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "AI Bootcamp Final API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "checkpoints": "available",
            "retriever": "available",
            "workflow": "available",
            "history": "available"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
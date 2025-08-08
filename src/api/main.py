import uvicorn
from fastapi import FastAPI

# 절대 경로 임포트로 수정
from src.api.routes import workflow, checkpoints, retriever, history, feedback, supervisor

# 데이터베이스 초기화를 위한 임포트 추가
from src.core.storage.database import Base, engine

# 데이터베이스 초기화
Base.metadata.create_all(bind=engine)

# FastAPI 인스턴스 생성
app = FastAPI(
    title="AI Knowledge Graph System API",
    description="키워드 기반 지식 그래프 및 실시간 위키 생성 시스템 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Health check 엔드포인트 추가
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "AI Knowledge Graph System API is running"}

@app.get("/api/v1/health")
async def health_check_v1():
    return {"status": "healthy", "message": "AI Knowledge Graph System API v1 is running"}

# router 추가
app.include_router(history.router)
app.include_router(workflow.router)
app.include_router(checkpoints.router)
app.include_router(retriever.router, prefix="/api/v1")
app.include_router(supervisor.router)
# 피드백 라우터를 먼저 등록 (더 구체적인 경로가 먼저)
app.include_router(feedback.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

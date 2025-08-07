#!/usr/bin/env python3
"""
환경 테스트용 간단한 FastAPI 앱
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="AI Knowledge Graph System - Test",
    description="환경 테스트용 기본 API",
    version="0.1.0",
)

@app.get("/")
async def root():
    """기본 엔드포인트"""
    return {"message": "🤖 AI Knowledge Graph System - 환경 테스트 성공!"}

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "message": "시스템이 정상적으로 작동 중입니다",
        "environment": {
            "python_version": "3.13+",
            "has_azure_openai_key": bool(os.getenv("AZURE_OPENAI_API_KEY")),
            # "has_serpapi_key": bool(os.getenv("SERPAPI_KEY")),  # SerpAPI 제거
        }
    }

@app.get("/env-test")
async def env_test():
    """환경변수 테스트"""
    env_vars = {
        "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
        "AZURE_OPENAI_API_KEY": bool(os.getenv("AZURE_OPENAI_API_KEY")),
        "AZURE_OPENAI_DEPLOY_GPT4O": bool(os.getenv("AZURE_OPENAI_DEPLOY_GPT4O")),
        "RDFLIB_STORE_URI": os.getenv("RDFLIB_STORE_URI", "기본값 없음"),
        "REDIS_URL": os.getenv("REDIS_URL", "기본값 없음"),
    }
    
    return {
        "message": "환경변수 상태",
        "env_status": env_vars,
        "recommendations": [
            "✅ 기본 설정이 완료되었습니다" if env_vars["AZURE_OPENAI_API_KEY"] 
            else "⚠️ Azure OpenAI API 키를 설정해주세요",
                    "✅ 데이터베이스 설정 확인됨" if env_vars["RDFLIB_STORE_URI"] != "기본값 없음"
        else "⚠️ RDFLib Store URI 설정을 확인해주세요"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 테스트 서버 시작 중...")
    print("📍 URL: http://localhost:8000")
    print("📍 API 문서: http://localhost:8000/docs")
    print("📍 헬스체크: http://localhost:8000/health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
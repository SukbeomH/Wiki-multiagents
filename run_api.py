#!/usr/bin/env python3
"""
AI Knowledge Graph System API 서버 실행 스크립트

새로운 src 구조에 맞게 API 서버를 실행합니다.
"""

import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from src.api.main import app
    
    print("🚀 AI Knowledge Graph System API 서버를 시작합니다...")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔍 ReDoc 문서: http://localhost:8000/redoc")
    
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    ) 
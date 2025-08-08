FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치 (필요시 확장)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (API는 src 이하에 위치)
COPY src/ ./src

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# FastAPI 실행 (uvicorn, --reload는 compose에서 코드 마운트 시 핫리로드 동작)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

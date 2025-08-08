# 환경설정 가이드

## 필수 설정 단계

1. **환경변수 파일 생성**
   ```bash
   cp config/environment.template .env
   ```

2. **필수 환경변수 설정**
   
   ### Azure OpenAI (선택: LLM 사용 시)
   - `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 리소스 엔드포인트
   - `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
   - `AZURE_OPENAI_DEPLOY_GPT4O`: GPT-4o 배포 이름

   LLM 미사용 환경에서도 시스템은 동작하며, 기본 규칙 기반 폴백 응답을 사용합니다.

3. **데이터베이스/스토리지 설정**
   
   - `RDFLIB_STORE_URI=sqlite:///./data/kg.db`
   - `CACHE_DIR=./data/cache` (diskcache)
   - `LOCK_DIR=./data/locks` (filelock)

## 개발 환경 시작

```bash
# 1. 환경변수 설정
cp config/environment.template .env
# .env 파일을 편집하여 필요한 값들을 입력

# 2. Docker Compose로 서비스 시작 (선택)
docker-compose up -d

# 3. 로컬 개발 (수동)
# Terminal 1: FastAPI
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Streamlit
API_BASE_URL=http://localhost:8000/api/v1 streamlit run app/main.py
```

## 서비스 접근
- Streamlit UI: `http://localhost:8501`
- FastAPI: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`

## 프로덕션 배포 시 추가 고려사항
- JWT_SECRET_KEY: 강력한 비밀키 생성
- HTTPS 및 프록시 설정
- 방화벽 규칙 설정
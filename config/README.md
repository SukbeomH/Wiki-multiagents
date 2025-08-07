# 환경설정 가이드

## 필수 설정 단계

1. **환경변수 파일 생성**
   ```bash
   cp config/environment.template .env
   ```

2. **필수 환경변수 설정**
   
   ### Azure OpenAI (필수)
   - `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 리소스 엔드포인트
   - `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
   - `AZURE_OPENAI_DEPLOY_GPT4O`: GPT-4o 배포 이름

   ### 검색 API (선택사항)
   <!-- - `SERPAPI_KEY`: SerpAPI 키 (향상된 검색 기능용) --> <!-- SerpAPI 제거, DuckDuckGo만 사용 -->

3. **데이터베이스 설정**
   
   Docker Compose를 사용하는 경우 기본값 사용:
   - `RDFLIB_STORE_URI=sqlite:///./data/kg.db`
   - `REDIS_URL=redis://localhost:6379`

## 개발 환경 시작

```bash
# 1. 환경변수 설정
cp config/environment.template .env
# .env 파일을 편집하여 필요한 값들을 입력

# 2. Docker Compose로 서비스 시작
docker-compose up -d

# 3. 서비스 확인
# - Streamlit UI: http://localhost:8501
# - FastAPI: http://localhost:8000
# - Redis Commander: http://localhost:8081 (dev 프로필)
```

## 프로덕션 배포 시 추가 고려사항

- JWT_SECRET_KEY: 강력한 비밀키 생성
- 데이터베이스 비밀번호 변경
- HTTPS 설정
- 방화벽 규칙 설정
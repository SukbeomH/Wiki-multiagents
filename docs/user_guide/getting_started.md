# 사용자 시작 가이드

## 🚀 빠른 시작

### 1. 시스템 요구사항

- **Python**: 3.11 이상
- **메모리**: 최소 8GB RAM (권장 16GB)
- **디스크**: 최소 10GB 여유 공간
- **네트워크**: 인터넷 연결 (웹 검색용)

### 2. 환경 설정

```bash
# 1. 리포지토리 클론
git clone <repository-url>
cd aibootcamp-final

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp config/environment.template .env
# .env 파일을 편집하여 Azure OpenAI 설정
```

### 3. 필수 환경변수 설정

```bash
# Azure OpenAI (필수)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOY_GPT4O=your_gpt4o_deployment

# 선택적 설정
DEBUG=true  # 개발 모드
LOG_LEVEL=INFO  # 로그 레벨
```

### 4. 시스템 시작

#### Docker로 시작 (권장)
```bash
# 전체 시스템 시작
docker-compose up -d

# 개발 도구 포함
docker-compose --profile dev up -d
```

#### 로컬 개발 환경
```bash
# Terminal 1: FastAPI 백엔드
cd server && uvicorn main:app --reload

# Terminal 2: Streamlit 프론트엔드
cd app && streamlit run main.py
```

## 🎯 기본 사용법

### 1. 웹 인터페이스 접속

- **Streamlit UI**: http://localhost:8501
- **API 문서**: http://localhost:8000/docs

### 2. 첫 번째 지식 그래프 생성

1. **키워드 입력**: 관심 주제 키워드 입력 (예: "artificial intelligence")
2. **검색 실행**: "Search" 버튼 클릭
3. **결과 확인**: 
   - 그래프 탭에서 시각적 지식 맵 확인
   - 위키 탭에서 생성된 문서 확인

### 3. 그래프 탐색

- **노드 클릭**: 엔티티 상세 정보 확인
- **드래그**: 그래프 이동
- **줌**: 마우스 휠로 확대/축소
- **연결선**: 엔티티 간 관계 확인

### 4. 위키 문서 편집

- **문서 수정**: 위키 탭에서 직접 편집
- **피드백 제출**: "Submit Feedback" 버튼으로 개선 제안
- **자동 업데이트**: 시스템이 피드백을 반영하여 재생성

## 🔧 고급 기능

### 1. API 직접 사용

```python
import requests

# 키워드 검색
response = requests.post("http://localhost:8000/api/v1/research", 
    json={"keyword": "machine learning"})

# 결과 확인
data = response.json()
print(f"수집된 문서: {len(data['docs'])}개")
```

### 2. 체크포인트 관리

```python
# 체크포인트 저장
checkpoint_data = {
    "workflow_id": "my-workflow",
    "checkpoint_type": "manual",
    "state_snapshot": {...}
}

response = requests.post("http://localhost:8000/api/v1/checkpoints", 
    json=checkpoint_data)
```

### 3. 성능 모니터링

```bash
# 시스템 상태 확인
curl http://localhost:8000/api/v1/health

# 캐시 정보 확인
curl http://localhost:8000/api/v1/cache/info
```

## 🛠️ 문제 해결

### 일반적인 문제들

#### 1. Azure OpenAI 연결 오류
```bash
# 환경변수 확인
echo $AZURE_OPENAI_ENDPOINT
echo $AZURE_OPENAI_API_KEY

# API 키 유효성 테스트
curl -H "api-key: $AZURE_OPENAI_API_KEY" \
     "$AZURE_OPENAI_ENDPOINT/openai/deployments/$AZURE_OPENAI_DEPLOY_GPT4O?api-version=2024-02-15-preview"
```

#### 2. 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :8000  # FastAPI
lsof -i :8501  # Streamlit

# 다른 포트로 실행
uvicorn main:app --reload --port 8001
streamlit run main.py --server.port 8502
```

#### 3. 메모리 부족
```bash
# 메모리 사용량 확인
free -h

# 캐시 정리
rm -rf data/cache/*
```

### 로그 확인

```bash
# Docker 로그
docker-compose logs -f

# 애플리케이션 로그
tail -f logs/app.log
```

## 📚 추가 리소스

- **API 문서**: http://localhost:8000/docs
- **프로젝트 구조**: [docs/architecture/project_structure.md](../architecture/project_structure.md)
- **성능 최적화**: [performance_optimization_report.md](../performance_optimization_report.md)
- **마이그레이션 가이드**: [migration_summary.md](../architecture/migration_summary.md)

## 🤝 지원

- **이슈 리포트**: GitHub Issues
- **기능 요청**: GitHub Discussions
- **문서 개선**: Pull Request

---

*마지막 업데이트: 2025-08-07* 
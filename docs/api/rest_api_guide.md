# REST API 가이드

## 📋 개요

AI Knowledge Graph System은 FastAPI 기반의 REST API를 제공합니다. 이 가이드는 API 사용법과 예제를 포함합니다.

## 🔗 기본 정보

- **Base URL**: `http://localhost:8000`
- **API 문서**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc 문서**: `http://localhost:8000/redoc`
- **API 버전**: v1

## 🚀 인증

현재 버전에서는 인증이 필요하지 않습니다. 향후 OAuth2 기반 인증이 추가될 예정입니다.

## 📡 주요 엔드포인트

### 1. 헬스체크

#### 시스템 상태 확인
```http
GET /health
```

**응답 예시**:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-07T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "api": "healthy",
    "cache": "healthy",
    "vector_store": "healthy"
  }
}
```

### 2. Research Agent API

#### 키워드 기반 문서 수집
```http
POST /api/v1/research
Content-Type: application/json

{
  "keyword": "artificial intelligence",
  "top_k": 10
}
```

**응답 예시**:
```json
{
  "docs": [
    "Artificial intelligence (AI) is intelligence demonstrated by machines...",
    "Machine learning is a subset of artificial intelligence..."
  ],
  "metadata": [
    {
      "title": "Artificial Intelligence - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "snippet": "Artificial intelligence (AI) is intelligence..."
    }
  ],
  "cache_hit": false,
  "processing_time": 1.284
}
```

### 3. Extractor Agent API

#### 엔티티 및 관계 추출
```http
POST /api/v1/extract
Content-Type: application/json

{
  "docs": [
    "Artificial intelligence (AI) is intelligence demonstrated by machines...",
    "Machine learning is a subset of artificial intelligence..."
  ]
}
```

**응답 예시**:
```json
{
  "entities": [
    {
      "id": "ent_001",
      "type": "concept",
      "name": "Artificial Intelligence",
      "confidence": 0.95,
      "extra": {
        "aliases": ["AI", "Machine Intelligence"]
      }
    }
  ],
  "relations": [
    {
      "source": "ent_001",
      "target": "ent_002", 
      "predicate": "related_to",
      "confidence": 0.88
    }
  ],
  "processing_time": 2.156
}
```

### 4. Retriever Agent API

#### 유사 문서 검색 (RAG)
```http
POST /api/v1/retrieve
Content-Type: application/json

{
  "query": "machine learning applications",
  "top_k": 5
}
```

**응답 예시**:
```json
{
  "doc_ids": ["doc_001", "doc_002", "doc_003"],
  "context": "Machine learning applications include...",
  "scores": [0.95, 0.87, 0.82],
  "processing_time": 0.234
}
```

### 5. Wiki Agent API

#### 위키 문서 생성
```http
POST /api/v1/wiki
Content-Type: application/json

{
  "node_id": "ent_001",
  "entities": [...],
  "relations": [...]
}
```

**응답 예시**:
```json
{
  "markdown": "# Artificial Intelligence\n\nArtificial Intelligence (AI) is...",
  "summary": "AI is a field of computer science...",
  "processing_time": 3.421
}
```

### 6. GraphViz Agent API

#### 그래프 시각화 데이터 생성
```http
POST /api/v1/graphviz
Content-Type: application/json

{
  "entities": [...],
  "relations": [...]
}
```

**응답 예시**:
```json
{
  "graph_json": {
    "nodes": [
      {
        "id": "ent_001",
        "label": "Artificial Intelligence",
        "type": "concept",
        "size": 20
      }
    ],
    "edges": [
      {
        "source": "ent_001",
        "target": "ent_002",
        "label": "related_to",
        "weight": 0.88
      }
    ]
  },
  "processing_time": 0.156
}
```

### 7. Checkpoint API

#### 체크포인트 저장
```http
POST /api/v1/checkpoints
Content-Type: application/json

{
  "workflow_id": "workflow_001",
  "checkpoint_type": "manual",
  "state_snapshot": {
    "trace_id": "trace_001",
    "keyword": "artificial intelligence",
    "current_stage": "research",
    "research_completed": true
  },
  "metadata": {
    "user": "admin",
    "stage": "data_collection"
  }
}
```

#### 체크포인트 조회
```http
GET /api/v1/checkpoints/{workflow_id}
```

#### 최신 체크포인트 조회
```http
GET /api/v1/checkpoints/{workflow_id}/latest
```

#### 체크포인트 삭제
```http
DELETE /api/v1/checkpoints/{workflow_id}
```

### 8. Workflow API

#### 워크플로우 시작
```http
POST /api/v1/workflow/start
Content-Type: application/json

{
  "keyword": "machine learning",
  "user_id": "user_001",
  "config": {
    "max_docs": 10,
    "extraction_confidence": 0.8
  }
}
```

#### 워크플로우 상태 조회
```http
GET /api/v1/workflow/{workflow_id}/status
```

#### 워크플로우 중단
```http
POST /api/v1/workflow/{workflow_id}/stop
```

### 9. History API

#### 워크플로우 히스토리 조회
```http
GET /api/v1/history
```

**쿼리 파라미터**:
- `page`: 페이지 번호 (기본값: 1)
- `size`: 페이지 크기 (기본값: 20)
- `user_id`: 사용자 ID 필터
- `status`: 상태 필터 (completed, failed, running)

#### 특정 워크플로우 히스토리
```http
GET /api/v1/history/{workflow_id}
```

## 🔧 에러 처리

### 에러 응답 형식
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "keyword",
      "issue": "Field is required"
    }
  },
  "timestamp": "2025-08-07T10:30:00Z",
  "request_id": "req_123456"
}
```

### 주요 에러 코드
- `VALIDATION_ERROR`: 입력 데이터 검증 실패
- `AGENT_ERROR`: AI 에이전트 처리 오류
- `STORAGE_ERROR`: 저장소 접근 오류
- `WORKFLOW_ERROR`: 워크플로우 실행 오류
- `RATE_LIMIT_ERROR`: 요청 제한 초과

## 📊 성능 고려사항

### 요청 제한
- **Research API**: 분당 10회
- **Extract API**: 분당 5회
- **Workflow API**: 분당 3회

### 응답 시간
- **헬스체크**: < 100ms
- **Research**: 1-3초
- **Extract**: 2-5초
- **Retrieve**: < 500ms
- **Wiki**: 3-8초
- **GraphViz**: < 1초

### 권장사항
1. **비동기 처리**: 긴 작업은 워크플로우 API 사용
2. **캐시 활용**: 동일한 키워드 재검색 시 캐시 히트
3. **배치 처리**: 여러 문서는 한 번에 처리
4. **타임아웃 설정**: 클라이언트에서 적절한 타임아웃 설정

## 🧪 테스트 예제

### Python 클라이언트 예제
```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 헬스체크
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.json()}")

# Research API 테스트
research_data = {
    "keyword": "artificial intelligence",
    "top_k": 5
}
response = requests.post(f"{BASE_URL}/api/v1/research", json=research_data)
result = response.json()
print(f"Found {len(result['docs'])} documents")

# Workflow API 테스트
workflow_data = {
    "keyword": "machine learning",
    "user_id": "test_user"
}
response = requests.post(f"{BASE_URL}/api/v1/workflow/start", json=workflow_data)
workflow_id = response.json()["workflow_id"]
print(f"Started workflow: {workflow_id}")
```

### cURL 예제
```bash
# 헬스체크
curl -X GET "http://localhost:8000/health"

# Research API
curl -X POST "http://localhost:8000/api/v1/research" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "artificial intelligence", "top_k": 5}'

# Workflow 시작
curl -X POST "http://localhost:8000/api/v1/workflow/start" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "machine learning", "user_id": "test_user"}'
```

## 📚 추가 리소스

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI 스키마**: http://localhost:8000/openapi.json
- **프로젝트 문서**: [docs/](../)

---

*마지막 업데이트: 2025-08-07* 
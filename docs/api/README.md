# API 문서

## 개요

AI Knowledge Graph System의 REST API 문서입니다. 이 API는 FastAPI를 기반으로 구축되었으며, 새로운 `src` 구조를 사용합니다.

## 기본 정보

- **Base URL**: `http://localhost:8000`
- **API 문서**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc 문서**: `http://localhost:8000/redoc`
- **OpenAPI 스키마**: `http://localhost:8000/openapi.json`

## 인증

현재 API는 인증이 필요하지 않습니다. (단순화 계획: 인증/권한은 후속 단계로 이관)

## 엔드포인트

### 1. 헬스 체크

#### GET `/health`

시스템의 전반적인 상태를 확인합니다.

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-07T17:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "cache": "healthy",
    "vector_store": "healthy"
  }
}
```

### 2. 워크플로우 (단순화 Flow)

#### POST `/workflow/debate`

지식 그래프 워크플로우를 시작합니다. 내부적으로 LangGraph 기반의 단순 직렬 흐름(Research → Extract → Retrieve → Wiki → GraphViz)을 수행하며, 각 단계는 filelock 기반 락과 고정 지연 재시도(RetryManager), 체크포인트(CheckpointManager)를 통해 기본적인 견고성을 갖습니다.

**요청 본문:**
```json
{
  "keyword": "인공지능",
  "max_documents": 10,
  "language": "ko",
  "workflow_type": "knowledge_graph"
}
```

**응답 예시:**
```json
{
  "workflow_id": "wf_1234567890",
  "status": "started",
  "message": "워크플로우가 성공적으로 시작되었습니다.",
  "estimated_duration": "5-10분"
}
```

#### GET `/workflow/{workflow_id}/status`

워크플로우의 현재 상태를 조회합니다.

**응답 예시:**
```json
{
  "workflow_id": "wf_1234567890",
  "status": "in_progress",
  "current_stage": "extraction",
  "progress": 60,
  "started_at": "2025-08-07T17:30:00Z",
  "estimated_completion": "2025-08-07T17:35:00Z"
}
```

#### GET `/workflow/{workflow_id}/result`

워크플로우 결과를 조회합니다.

**응답 예시:**
```json
{
  "workflow_id": "wf_1234567890",
  "status": "completed",
  "result": {
    "entities": [
      {
        "id": "entity_1",
        "name": "머신러닝",
        "type": "CONCEPT",
        "confidence": 0.95
      }
    ],
    "relations": [
      {
        "id": "relation_1",
        "source": "entity_1",
        "target": "entity_2",
        "type": "RELATED_TO",
        "confidence": 0.88
      }
    ],
    "documents": [
      {
        "id": "doc_1",
        "title": "머신러닝 기초",
        "content": "...",
        "url": "https://example.com",
        "relevance_score": 0.92
      }
    ]
  }
}
```

### 3. 체크포인트 (CheckpointManager)

#### GET `/checkpoints/{workflow_id}`

워크플로우의 체크포인트를 조회합니다.

**응답 예시:**
```json
{
  "workflow_id": "wf_1234567890",
  "checkpoints": [
    {
      "checkpoint_id": "cp_1",
      "checkpoint_type": "stage_completion",
      "stage": "research",
      "timestamp": "2025-08-07T17:31:00Z",
      "data": {
        "documents_collected": 15,
        "processing_time": 120
      }
    }
  ]
}
```

#### POST `/checkpoints/{workflow_id}`

새로운 체크포인트를 생성합니다.

**요청 본문:**
```json
{
  "checkpoint_type": "manual",
  "stage": "extraction",
  "data": {
    "entities_extracted": 25,
    "relations_found": 12
  }
}
```

### 4. 검색 (FAISS Retriever)

#### POST `/retriever/search`

벡터 검색을 수행합니다.

**요청 본문:**
```json
{
  "query": "머신러닝 알고리즘",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "include_metadata": true
}
```

**응답 예시:**
```json
{
  "query": "머신러닝 알고리즘",
  "results": [
    {
      "document_id": "doc_1",
      "title": "머신러닝 기초",
      "content": "...",
      "similarity_score": 0.92,
      "metadata": {
        "url": "https://example.com",
        "published_date": "2025-01-01"
      }
    }
  ],
  "total_results": 5,
  "search_time": 0.15
}
```

### 5. 히스토리

#### GET `/history`

워크플로우 히스토리를 조회합니다.

**쿼리 파라미터:**
- `limit`: 조회할 항목 수 (기본값: 10)
- `offset`: 건너뛸 항목 수 (기본값: 0)
- `status`: 상태별 필터링 (예: "completed", "failed")

**응답 예시:**
```json
{
  "history": [
    {
      "workflow_id": "wf_1234567890",
      "keyword": "인공지능",
      "status": "completed",
      "started_at": "2025-08-07T17:30:00Z",
      "completed_at": "2025-08-07T17:35:00Z",
      "total_processing_time": 300,
      "entities_count": 25,
      "relations_count": 12
    }
  ],
  "total_count": 50,
  "has_more": true
}
```

#### POST `/history`

새로운 히스토리 항목을 저장합니다.

**요청 본문:**
```json
{
  "workflow_id": "wf_1234567890",
  "keyword": "인공지능",
  "status": "completed",
  "metadata": {
    "entities_count": 25,
    "relations_count": 12,
    "documents_processed": 15
  }
}
```

## 에러 응답

모든 API 엔드포인트는 일관된 에러 응답 형식을 사용합니다:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 데이터가 유효하지 않습니다.",
    "details": {
      "field": "keyword",
      "issue": "필수 필드입니다."
    }
  },
  "timestamp": "2025-08-07T17:30:00Z",
  "request_id": "req_1234567890"
}
```

### 일반적인 에러 코드

- `VALIDATION_ERROR`: 요청 데이터 검증 실패
- `WORKFLOW_NOT_FOUND`: 워크플로우를 찾을 수 없음
- `WORKFLOW_ALREADY_RUNNING`: 워크플로우가 이미 실행 중
- `INTERNAL_SERVER_ERROR`: 서버 내부 오류
- `SERVICE_UNAVAILABLE`: 서비스 일시적 사용 불가

## 요청 제한

- **Rate Limit**: 분당 100 요청
- **최대 요청 크기**: 10MB
- **타임아웃**: 30초

## 예제

### cURL 예제

```bash
# 워크플로우 시작
curl -X POST "http://localhost:8000/workflow/debate" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "인공지능",
    "max_documents": 10,
    "language": "ko"
  }'

# 워크플로우 상태 조회
curl -X GET "http://localhost:8000/workflow/wf_1234567890/status"

# 검색 수행
curl -X POST "http://localhost:8000/retriever/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "머신러닝 알고리즘",
    "top_k": 5
  }'
```

### Python 예제

```python
import requests

# API 기본 설정
BASE_URL = "http://localhost:8000"

# 워크플로우 시작
response = requests.post(f"{BASE_URL}/workflow/debate", json={
    "keyword": "인공지능",
    "max_documents": 10,
    "language": "ko"
})

workflow_id = response.json()["workflow_id"]

# 상태 조회
status_response = requests.get(f"{BASE_URL}/workflow/{workflow_id}/status")
print(status_response.json())

# 결과 조회
result_response = requests.get(f"{BASE_URL}/workflow/{workflow_id}/result")
print(result_response.json())
```

## 버전 관리

API 버전은 URL 경로에 포함됩니다. 현재 버전은 v1입니다.

- **현재 버전**: v1
- **호환성**: 하위 호환성 보장
- **Deprecation**: 최소 6개월 전 공지

## 지원

API 관련 문의사항이나 버그 리포트는 GitHub Issues를 통해 제출해 주세요. 
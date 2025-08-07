# 마이그레이션 매핑 문서

## 1. 파일 이동 매핑

### 1.1 에이전트 파일 이동

#### Research Agent
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/agents/research/__init__.py` | `src/agents/research/__init__.py` | 이동 필요 |
| `server/agents/research/agent.py` | `src/agents/research/agent.py` | 이동 필요 |
| `server/agents/research/client.py` | `src/agents/research/client.py` | 이동 필요 |
| `server/agents/research/cache.py` | `src/agents/research/cache.py` | 이동 필요 |
| `server/agents/research/config.py` | `src/agents/research/config.py` | 이동 필요 |

#### Retriever Agent
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/agents/retriever/__init__.py` | `src/agents/retriever/__init__.py` | 이동 필요 |
| `server/agents/retriever/agent.py` | `src/agents/retriever/agent.py` | 이동 필요 |

#### Vector Store
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/retrieval/vector_store.py` | `src/core/storage/vector_store/faiss_store.py` | 이동 필요 |

#### 기타 에이전트들
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/agents/extractor/*` | `src/agents/extractor/*` | 이동 필요 |
| `server/agents/wiki/*` | `src/agents/wiki/*` | 이동 필요 |
| `server/agents/graphviz/*` | `src/agents/graphviz/*` | 이동 필요 |
| `server/agents/supervisor/*` | `src/agents/supervisor/*` | 이동 필요 |
| `server/agents/feedback/*` | `src/agents/feedback/*` | 이동 필요 |

### 1.2 핵심 기능 파일 이동

#### 스키마
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/schemas/base.py` | `src/core/schemas/base.py` | 이동 필요 |
| `server/schemas/agents.py` | `src/core/schemas/agents.py` | 이동 필요 |

#### 유틸리티
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/utils/*` | `src/core/utils/*` | 이동 필요 |

#### 워크플로우
| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/workflow/*` | `src/core/workflow/*` | 이동 필요 |

### 1.3 API 파일 이동

| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `server/main.py` | `src/api/main.py` | 이동 필요 |
| `server/routers/*` | `src/api/routes/*` | 이동 필요 |

### 1.4 UI 파일 이동

| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `app/main.py` | `src/ui/main.py` | 이동 필요 |
| `app/components/*` | `src/ui/components/*` | 이동 필요 |
| `app/utils/*` | `src/ui/utils/*` | 이동 필요 |

## 2. Import 경로 변경

### 2.1 에이전트 Import 변경

#### Before
```python
from server.agents.research import ResearchAgent
from server.agents.retriever import RetrieverAgent
from server.agents.extractor import ExtractorAgent
```

#### After
```python
from src.agents.research import ResearchAgent
from src.agents.retriever import RetrieverAgent
from src.agents.extractor import ExtractorAgent
```

### 2.2 스키마 Import 변경

#### Before
```python
from server.schemas.base import BaseMessage
from server.schemas.agents import ResearchIn, ResearchOut
```

#### After
```python
from src.core.schemas.base import BaseMessage
from src.core.schemas.agents import ResearchIn, ResearchOut
```

### 2.3 유틸리티 Import 변경

#### Before
```python
from server.utils.logging import setup_logger
```

#### After
```python
from src.core.utils.logging import setup_logger
```

### 2.4 벡터 스토어 Import 변경

#### Before
```python
from server.retrieval.vector_store import FAISSVectorStore
```

#### After
```python
from src.core.storage.vector_store.faiss_store import FAISSVectorStore
```

## 3. 설정 파일 변경

### 3.1 Dockerfile 경로 변경

#### server/Dockerfile
```dockerfile
# Before
COPY server/ /app/server/
WORKDIR /app/server

# After
COPY src/ /app/src/
WORKDIR /app/src/api
```

#### app/Dockerfile
```dockerfile
# Before
COPY app/ /app/app/
WORKDIR /app/app

# After
COPY src/ui/ /app/src/ui/
WORKDIR /app/src/ui
```

### 3.2 pytest.ini 설정 변경

```ini
# Before
testpaths = tests server

# After
testpaths = tests src
```

### 3.3 requirements.txt 경로 변경

```txt
# Before
-e ./server

# After
-e ./src
```

## 4. 테스트 파일 이동

### 4.1 테스트 구조 개선

| 현재 경로 | 새 경로 | 상태 |
|----------|---------|------|
| `tests/agents/test_research_agent.py` | `tests/unit/agents/test_research_agent.py` | 이동 필요 |
| `tests/agents/test_research_agent_performance.py` | `tests/performance/agents/test_research_agent.py` | 이동 필요 |
| `tests/schemas/test_research_schemas.py` | `tests/unit/core/test_schemas.py` | 이동 필요 |
| `tests/unit/test_vector_store_benchmark.py` | `tests/performance/core/test_vector_store.py` | 이동 필요 |

## 5. 마이그레이션 체크리스트

### 5.1 Phase 1: 기반 구조 구축
- [ ] `src/` 디렉토리 생성
- [ ] `src/agents/` 디렉토리 생성
- [ ] `src/core/` 디렉토리 생성
- [ ] `src/api/` 디렉토리 생성
- [ ] `src/ui/` 디렉토리 생성
- [ ] 각 디렉토리에 `__init__.py` 추가

### 5.2 Phase 2: 파일 이동
- [ ] Research Agent 파일 이동
- [ ] Retriever Agent 파일 이동
- [ ] Vector Store 파일 이동
- [ ] 스키마 파일 이동
- [ ] 유틸리티 파일 이동
- [ ] API 파일 이동
- [ ] UI 파일 이동

### 5.3 Phase 3: Import 경로 수정
- [ ] 모든 Python 파일의 import 경로 수정
- [ ] 상대 경로 import 검토 및 수정
- [ ] 순환 import 문제 해결

### 5.4 Phase 4: 설정 파일 업데이트
- [ ] Dockerfile 경로 수정
- [ ] pytest.ini 설정 업데이트
- [ ] requirements.txt 경로 수정
- [ ] CI/CD 설정 업데이트

### 5.5 Phase 5: 테스트 및 검증
- [ ] 모든 단위 테스트 통과 확인
- [ ] 통합 테스트 통과 확인
- [ ] 성능 테스트 통과 확인
- [ ] E2E 테스트 통과 확인

## 6. 롤백 계획

### 6.1 롤백 시나리오
1. **기능 손실 발생**: 이전 구조로 즉시 복원
2. **Import 오류 발생**: 점진적 롤백
3. **CI/CD 실패**: 설정 파일 롤백

### 6.2 롤백 방법
```bash
# Git을 사용한 롤백
git checkout HEAD~1 -- server/ app/ tests/

# 수동 롤백
mv src/agents/research/* server/agents/research/
mv src/core/schemas/* server/schemas/
# ... 기타 파일들
```

---

**작성일**: 2025-08-07  
**작성자**: AI Assistant  
**버전**: 1.0
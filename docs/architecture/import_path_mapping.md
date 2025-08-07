# Import 경로 매핑 가이드

## 개요

이 문서는 기존 `server.` 기반 import 경로를 새로운 `src.` 기반 구조로 변경하는 매핑 가이드를 제공합니다.

## Import 경로 변경 원칙

### 1. 절대 경로 사용
- 상대 경로 대신 절대 경로 사용 권장
- 명확성과 유지보수성 향상

### 2. 계층적 구조
- `src.` 루트에서 시작하는 계층적 구조
- 기능별 명확한 분리

### 3. 일관성 유지
- 모든 모듈에서 동일한 패턴 적용
- 테스트 코드도 동일한 패턴 적용

## Import 경로 매핑 테이블

### 1. 에이전트 관련 Import

#### Research Agent
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.agents.research.client import DuckDuckGoClient` | `from src.agents.research.client import DuckDuckGoClient` | ⏳ 대기 | |
| `from server.agents.research.cache import ResearchCache` | `from src.agents.research.cache import ResearchCache` | ⏳ 대기 | |
| `from server.agents.research.agent import ResearchAgent` | `from src.agents.research.agent import ResearchAgent` | ⏳ 대기 | |
| `from server.agents.research.config import PERFORMANCE_CONFIG` | `from src.agents.research.config import PERFORMANCE_CONFIG` | ⏳ 대기 | |
| `from server.agents.research import ResearchAgent` | `from src.agents.research import ResearchAgent` | ⏳ 대기 | |

#### Retriever Agent
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.agents.retriever import get_retriever_agent, RetrieverAgent` | `from src.agents.retriever import get_retriever_agent, RetrieverAgent` | ⏳ 대기 | |

### 2. 스키마 관련 Import

#### 기본 스키마
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.schemas.base import WorkflowState, WorkflowStage` | `from src.core.schemas.base import WorkflowState, WorkflowStage` | ⏳ 대기 | |
| `from server.schemas.base import CheckpointData, CheckpointType` | `from src.core.schemas.base import CheckpointData, CheckpointType` | ⏳ 대기 | |
| `from server.schemas.base import MessageBase` | `from src.core.schemas.base import MessageBase` | ⏳ 대기 | |

#### 에이전트 스키마
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.schemas.agents import ResearchIn, ResearchOut` | `from src.core.schemas.agents import ResearchIn, ResearchOut` | ⏳ 대기 | |
| `from server.schemas.agents import RetrieverIn, RetrieverOut` | `from src.core.schemas.agents import RetrieverIn, RetrieverOut` | ⏳ 대기 | |

### 3. 저장소 관련 Import

#### 벡터 스토어
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.retrieval.vector_store import FAISSVectorStore` | `from src.core.storage.vector_store.vector_store import FAISSVectorStore` | ⏳ 대기 | |
| `from server.retrieval.vector_store import FAISSVectorStoreConfig` | `from src.core.storage.vector_store.vector_store import FAISSVectorStoreConfig` | ⏳ 대기 | |

#### 지식 그래프
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.kg_manager import RDFLibKnowledgeGraphManager` | `from src.core.storage.knowledge_graph.kg_manager import RDFLibKnowledgeGraphManager` | ⏳ 대기 | |

### 4. 유틸리티 관련 Import

#### 설정
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.config import settings` | `from src.core.utils.config import settings` | ⏳ 대기 | |

#### 캐시 관리
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.cache_manager import CacheManager, CacheConfig` | `from src.core.utils.cache_manager import CacheManager, CacheConfig` | ⏳ 대기 | |

#### 락 관리
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.lock_manager import DistributedLockManager, LockInfo` | `from src.core.utils.lock_manager import DistributedLockManager, LockInfo` | ⏳ 대기 | |

#### 저장소 관리
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.storage_manager import StorageManager, RedisConfig` | `from src.core.utils.storage_manager import StorageManager, RedisConfig` | ⏳ 대기 | |

#### 스케줄러
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.utils.scheduler import *` | `from src.core.utils.scheduler import *` | ⏳ 대기 | |

### 5. API 관련 Import

#### 메인 앱
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.main import app` | `from src.api.main import app` | ⏳ 대기 | |

#### 라우터
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.routers import history` | `from src.api.routes import history` | ⏳ 대기 | |

### 6. 데이터베이스 관련 Import

#### 모델
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.db.models import Debate as DebateModel` | `from src.core.storage.history.models import Debate as DebateModel` | ⏳ 대기 | |

#### 스키마
| 현재 경로 | 새 경로 | 상태 | 비고 |
|-----------|---------|------|------|
| `from server.db.schemas import DebateSchema, DebateCreate` | `from src.core.storage.history.schemas import DebateSchema, DebateCreate` | ⏳ 대기 | |

## Import 경로 변경 우선순위

### Phase 1: 핵심 기능 (높은 우선순위)
1. **스키마 Import**: `server.schemas` → `src.core.schemas`
2. **저장소 Import**: `server.retrieval` → `src.core.storage`
3. **유틸리티 Import**: `server.utils` → `src.core.utils`

### Phase 2: 에이전트 (중간 우선순위)
1. **Research Agent Import**: `server.agents.research` → `src.agents.research`
2. **Retriever Agent Import**: `server.agents.retriever` → `src.agents.retriever`
3. **기타 에이전트 Import**: 구현 후 마이그레이션

### Phase 3: API 및 UI (낮은 우선순위)
1. **API Import**: `server` → `src.api`
2. **UI Import**: `app` → `src.ui`

### Phase 4: 테스트 (마지막)
1. **테스트 Import**: 모든 테스트 파일의 import 경로 업데이트

## 자동화 스크립트

### Python 스크립트로 일괄 변경
```python
import os
import re

def update_imports(file_path):
    """파일의 import 경로를 업데이트"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Import 경로 매핑
    replacements = [
        (r'from server\.schemas\.', 'from src.core.schemas.'),
        (r'from server\.retrieval\.', 'from src.core.storage.'),
        (r'from server\.utils\.', 'from src.core.utils.'),
        (r'from server\.agents\.research\.', 'from src.agents.research.'),
        (r'from server\.agents\.retriever\.', 'from src.agents.retriever.'),
        (r'from server\.', 'from src.api.'),
        (r'import server\.', 'import src.api.'),
    ]
    
    for old_pattern, new_pattern in replacements:
        content = re.sub(old_pattern, new_pattern, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    """디렉토리 내 모든 Python 파일 처리"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports(file_path)
                print(f"Updated: {file_path}")

# 사용 예시
# process_directory('src/')
# process_directory('tests/')
```

## 검증 체크리스트

### Import 경로 검증
- [ ] 모든 `server.` import가 `src.` 기반으로 변경됨
- [ ] 상대 경로가 절대 경로로 변경됨
- [ ] 순환 의존성이 없음
- [ ] 모든 모듈이 정상적으로 import됨

### 기능 검증
- [ ] 테스트 실행 성공
- [ ] API 엔드포인트 정상 동작
- [ ] 에이전트 기능 정상 동작
- [ ] 워크플로우 정상 동작

### 성능 검증
- [ ] Import 시간 증가 없음
- [ ] 메모리 사용량 정상
- [ ] 응답 시간 유지

## 주의사항

### 1. 순환 의존성 방지
- `src.core`는 다른 모듈에 의존하지 않아야 함
- `src.agents`는 `src.core`에만 의존해야 함
- `src.api`는 `src.core`와 `src.agents`에 의존 가능

### 2. 테스트 코드 동기화
- 테스트 코드의 import 경로도 함께 업데이트
- Mock 객체의 경로도 업데이트 필요

### 3. 문서 업데이트
- README 파일의 import 예시 업데이트
- API 문서의 import 예시 업데이트

### 4. IDE 설정
- IDE의 Python 경로 설정 업데이트
- 자동 완성 및 리팩토링 기능 확인

## 롤백 계획

### 롤백 트리거
- Import 오류 발생
- 테스트 실패율 10% 이상
- 주요 기능 동작 불가

### 롤백 절차
1. Git 브랜치 생성 (`import-rollback`)
2. 기존 import 경로 복원
3. 테스트 실행 및 검증
4. 문제 분석 및 수정
5. 재시도

---

**마지막 업데이트**: 2025-01-27
**버전**: 1.0.0
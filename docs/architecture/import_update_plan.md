# Import 경로 업데이트 실행 계획

## 개요

이 문서는 실제 import 경로 변경을 위한 단계별 실행 계획을 제공합니다.

## 현재 상황 분석

### 발견된 Import 패턴
- **총 25개 파일**에서 `server.` 기반 import 발견
- **주요 패턴**:
  - `from server.schemas.` (스키마)
  - `from server.agents.` (에이전트)
  - `from server.utils.` (유틸리티)
  - `from server.retrieval.` (저장소)
  - `from server.routers.` (API 라우터)
  - `from server.main` (메인 앱)

### 영향받는 파일 분포
- **서버 코드**: 15개 파일
- **테스트 코드**: 10개 파일
- **총 변경 예정**: 25개 파일

## 단계별 실행 계획

### Phase 1: 준비 작업 (현재 단계)

#### 1.1 파일 마이그레이션 완료
- [ ] 13.5 Research Agent 마이그레이션
- [ ] 13.6 Extractor Agent 마이그레이션
- [ ] 13.7 Retriever Agent 마이그레이션
- [ ] 13.8 Wiki Agent 마이그레이션
- [ ] 13.9 GraphViz Agent 마이그레이션
- [ ] 13.10 Supervisor & Feedback Agents 마이그레이션
- [ ] 13.11 core 패키지 마이그레이션
- [ ] 13.12 API 마이그레이션
- [ ] 13.13 UI 마이그레이션

#### 1.2 백업 생성
```bash
# 현재 상태 백업
git add .
git commit -m "Backup before import path changes"
git tag backup-before-import-changes
```

### Phase 2: Import 경로 변경

#### 2.1 스크립트 실행
```bash
# Import 경로 변경 스크립트 실행
python scripts/update_imports.py . src tests
```

#### 2.2 변경사항 검증
```bash
# 변경사항 확인
cat import_changes_report.txt

# Python 문법 검사
find src tests -name "*.py" -exec python -m py_compile {} \;
```

#### 2.3 테스트 실행
```bash
# 단위 테스트
pytest tests/unit/ -v

# 통합 테스트
pytest tests/integration/ -v

# 성능 테스트
pytest tests/performance/ -v
```

### Phase 3: 검증 및 수정

#### 3.1 Import 오류 수정
- 누락된 import 경로 수정
- 순환 의존성 해결
- 상대 경로 → 절대 경로 변경

#### 3.2 테스트 실패 수정
- Mock 객체 경로 수정
- 테스트 fixture 경로 수정
- 테스트 설정 파일 수정

#### 3.3 기능 검증
- API 엔드포인트 테스트
- 에이전트 기능 테스트
- 워크플로우 테스트

## 예상 변경사항

### 1. 스키마 Import 변경
```python
# 변경 전
from server.schemas.base import WorkflowState, WorkflowStage
from server.schemas.agents import ResearchIn, ResearchOut

# 변경 후
from src.core.schemas.base import WorkflowState, WorkflowStage
from src.core.schemas.agents import ResearchIn, ResearchOut
```

### 2. 에이전트 Import 변경
```python
# 변경 전
from server.agents.research.client import DuckDuckGoClient
from server.agents.research.cache import ResearchCache
from server.agents.retriever import RetrieverAgent

# 변경 후
from src.agents.research.client import DuckDuckGoClient
from src.agents.research.cache import ResearchCache
from src.agents.retriever import RetrieverAgent
```

### 3. 유틸리티 Import 변경
```python
# 변경 전
from server.utils.config import settings
from server.utils.cache_manager import CacheManager
from server.retrieval.vector_store import FAISSVectorStore

# 변경 후
from src.core.utils.config import settings
from src.core.utils.cache_manager import CacheManager
from src.core.storage.vector_store.vector_store import FAISSVectorStore
```

### 4. API Import 변경
```python
# 변경 전
from server.main import app
from server.routers import history

# 변경 후
from src.api.main import app
from src.api.routes import history
```

## 위험 요소 및 대응 방안

### 1. 순환 의존성
**위험**: 모듈 간 순환 의존성 발생
**대응**: 
- 의존성 그래프 분석
- 인터페이스 분리
- 공통 기능을 `src.core`에 배치

### 2. Import 오류
**위험**: 파일 경로 변경 후 import 실패
**대응**:
- 단계별 마이그레이션
- 각 단계마다 테스트 실행
- 즉시 롤백 가능

### 3. 테스트 실패
**위험**: 테스트 코드의 import 경로 미변경
**대응**:
- 테스트 코드도 함께 업데이트
- Mock 객체 경로 수정
- 테스트 설정 파일 업데이트

## 검증 체크리스트

### Import 경로 검증
- [ ] 모든 `server.` import가 `src.` 기반으로 변경됨
- [ ] 상대 경로가 절대 경로로 변경됨
- [ ] 순환 의존성이 없음
- [ ] 모든 모듈이 정상적으로 import됨

### 기능 검증
- [ ] 단위 테스트 100% 통과
- [ ] 통합 테스트 100% 통과
- [ ] 성능 테스트 100% 통과
- [ ] API 엔드포인트 정상 동작
- [ ] 에이전트 기능 정상 동작
- [ ] 워크플로우 정상 동작

### 성능 검증
- [ ] Import 시간 증가 없음
- [ ] 메모리 사용량 정상
- [ ] 응답 시간 유지

## 롤백 계획

### 롤백 트리거
- Import 오류 발생
- 테스트 실패율 10% 이상
- 주요 기능 동작 불가

### 롤백 절차
```bash
# Git을 사용한 롤백
git checkout backup-before-import-changes
git checkout -b import-rollback
git add .
git commit -m "Rollback import path changes"
```

## 다음 단계

1. **파일 마이그레이션 완료**: 13.5-13.15 subtask 완료
2. **Import 경로 변경**: 스크립트 실행 및 검증
3. **테스트 및 검증**: 모든 테스트 통과 확인
4. **문서 업데이트**: README 및 API 문서 업데이트

---

**마지막 업데이트**: 2025-01-27
**버전**: 1.0.0
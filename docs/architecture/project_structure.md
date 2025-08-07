# 프로젝트 구조 문서

## 개요

이 문서는 AI Bootcamp Final 프로젝트의 디렉토리 구조와 모듈화된 아키텍처를 설명합니다.

## 디렉토리 구조

```
aibootcamp-final/
├── src/                          # 소스 코드 루트
│   ├── agents/                   # 에이전트 모듈
│   │   ├── research/            # Research Agent
│   │   ├── extractor/           # Extractor Agent
│   │   ├── retriever/           # Retriever Agent
│   │   ├── wiki/                # Wiki Agent
│   │   ├── graphviz/            # GraphViz Agent
│   │   ├── supervisor/          # Supervisor Agent
│   │   ├── feedback/            # Feedback Agent
│   │   └── __init__.py
│   ├── core/                    # 핵심 기능 모듈
│   │   ├── schemas/             # Pydantic 스키마
│   │   ├── storage/             # 데이터 저장소
│   │   ├── workflow/            # 워크플로우 관리
│   │   ├── utils/               # 유틸리티 함수
│   │   └── __init__.py
│   ├── api/                     # REST API
│   │   ├── routes/              # API 라우터
│   │   ├── middleware/          # 미들웨어
│   │   └── main.py              # FastAPI 앱
│   ├── ui/                      # 사용자 인터페이스
│   │   ├── components/          # UI 컴포넌트
│   │   ├── pages/               # 페이지
│   │   ├── utils/               # UI 유틸리티
│   │   └── main.py              # Streamlit 앱
│   ├── config/                  # 설정 관리
│   │   ├── settings.py          # 설정 클래스
│   │   ├── templates/           # 설정 템플릿
│   │   └── environment.template # 환경 변수 템플릿
│   └── __init__.py
├── tests/                       # 테스트 코드
│   ├── unit/                    # 단위 테스트
│   ├── integration/             # 통합 테스트
│   ├── e2e/                     # 엔드투엔드 테스트
│   └── conftest.py
├── docs/                        # 문서
│   ├── architecture/            # 아키텍처 문서
│   ├── api/                     # API 문서
│   ├── user_guide/              # 사용자 가이드
│   └── deployment/              # 배포 문서
├── data/                        # 데이터 디렉토리
│   ├── cache/                   # 캐시 파일
│   ├── vector_indices/          # 벡터 인덱스
│   └── locks/                   # 락 파일
├── config/                      # 기존 설정 (마이그레이션 중)
├── server/                      # 기존 서버 코드 (마이그레이션 중)
├── app/                         # 기존 UI 코드 (마이그레이션 중)
└── requirements.txt             # 의존성 파일
```

## 모듈 설명

### Agents 모듈

각 에이전트는 독립적인 패키지로 구성되어 있으며, 다음과 같은 구조를 가집니다:

```
src/agents/{agent_name}/
├── __init__.py          # 패키지 초기화
├── agent.py             # 메인 에이전트 클래스
├── client.py            # 외부 API 클라이언트 (필요시)
├── cache.py             # 캐시 관리 (필요시)
└── config.py            # 에이전트별 설정 (필요시)
```

### Core 모듈

핵심 기능을 제공하는 모듈들:

- **schemas**: Pydantic 기반 데이터 모델
- **storage**: 데이터베이스, 벡터 스토어, 캐시 관리
- **workflow**: LangGraph 기반 워크플로우 관리
- **utils**: 공통 유틸리티 함수

### API 모듈

FastAPI 기반 REST API:

- **routes**: 각 기능별 API 라우터
- **middleware**: 인증, 로깅, CORS 등 미들웨어
- **main.py**: FastAPI 애플리케이션 진입점

### UI 모듈

Streamlit 기반 사용자 인터페이스:

- **components**: 재사용 가능한 UI 컴포넌트
- **pages**: 페이지별 UI 로직
- **utils**: UI 관련 유틸리티
- **main.py**: Streamlit 애플리케이션 진입점

## 마이그레이션 상태

### 완료된 마이그레이션

- ✅ Research Agent → src/agents/research
- ✅ Extractor Agent → src/agents/extractor
- ✅ Retriever Agent → src/agents/retriever
- ✅ Wiki Agent → src/agents/wiki
- ✅ GraphViz Agent → src/agents/graphviz
- ✅ Supervisor Agent → src/agents/supervisor
- ✅ Feedback Agent → src/agents/feedback
- ✅ Core 스키마 및 유틸리티 → src/core
- ✅ API 라우터 → src/api/routes
- ✅ UI 애플리케이션 → src/ui
- ✅ 설정 관리 → src/config

### 진행중인 작업

- 🔄 환경 설정 모듈 통합
- 🔄 테스트 구조 통합
- 🔄 CI/CD 검증

## Import 경로 규칙

### 새로운 구조에서의 Import

```python
# 에이전트 import
from src.agents.research import ResearchAgent
from src.agents.extractor import ExtractorAgent

# Core 모듈 import
from src.core.schemas.agents import ResearchIn, ResearchOut
from src.core.storage.vector_store import FAISSVectorStore
from src.core.utils.cache_manager import CacheManager

# API import
from src.api.routes.checkpoints import router as checkpoints_router

# UI import
from src.ui.components.sidebar import render_sidebar
```

### 기존 코드와의 호환성

기존 코드는 점진적으로 새로운 구조로 마이그레이션되며, 
마이그레이션 중인 파일들은 `.old` 확장자로 백업됩니다.

## 다음 단계

1. 환경 설정 모듈 통합 완료
2. 테스트 구조 통합
3. CI/CD 파이프라인 업데이트
4. 기존 코드 정리 (server/, app/ 디렉토리 제거)
5. 문서 업데이트 
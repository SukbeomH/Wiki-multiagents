# 디렉토리 구조 설계 문서

## 1. 현재 구조 분석

### 현재 구조의 문제점
- `server/agents/` 하위에 모든 에이전트가 평면적으로 배치됨
- 각 에이전트별로 관련 파일들이 분산되어 있음
- 테스트 구조가 일관성이 없음
- 설정 파일들이 루트에 흩어져 있음

### 현재 구조
```
/
├── server/                    # 백엔드 서버
│   ├── agents/               # 에이전트들 (research, extractor, retriever, wiki, graphviz, supervisor, feedback)
│   ├── schemas/              # Pydantic 스키마
│   ├── utils/                # 유틸리티
│   ├── workflow/             # 워크플로우
│   ├── retrieval/            # 벡터 스토어
│   ├── routers/              # API 라우터
│   └── main.py               # FastAPI 앱
├── app/                      # Streamlit UI
│   ├── components/           # UI 컴포넌트
│   ├── utils/                # UI 유틸리티
│   └── main.py               # Streamlit 앱
├── tests/                    # 테스트
│   ├── agents/               # 에이전트 테스트
│   ├── schemas/              # 스키마 테스트
│   ├── unit/                 # 단위 테스트
│   ├── integration/          # 통합 테스트
│   └── e2e/                  # 엔드투엔드 테스트
├── docs/                     # 문서
├── config/                   # 설정
├── scripts/                  # 스크립트
└── requirements.txt          # 의존성
```

## 2. PRD 기반 새로운 구조 설계

### 2.1 전체 구조
```
src/                          # 소스 코드 루트
├── agents/                   # 멀티-에이전트 시스템
├── core/                     # 핵심 기능
├── api/                      # REST API (FastAPI)
└── ui/                       # Streamlit UI

config/                       # 설정 관리
tests/                        # 테스트 구조
docs/                         # 문서
```

### 2.2 상세 구조

#### src/agents/ - 멀티-에이전트 시스템
```
src/agents/
├── research/                # 문서 수집·캐싱 (DuckDuckGo API, LRU Cache)
│   ├── __init__.py
│   ├── agent.py             # ResearchAgent 클래스
│   ├── client.py            # DuckDuckGoClient
│   ├── cache.py             # ResearchCache
│   └── config.py            # PerformanceConfig
├── extractor/               # 엔티티·관계 추출 (Azure GPT-4o, Regex)
│   ├── __init__.py
│   ├── agent.py
│   ├── models.py            # 엔티티/관계 모델
│   └── prompts.py           # 프롬프트 템플릿
├── retriever/               # 유사 문서 선별 (FAISS IVF-HNSW)
│   ├── __init__.py
│   ├── agent.py
│   └── vector_store.py
├── wiki/                    # 위키 작성·요약 (Jinja2, GPT-4o)
│   ├── __init__.py
│   ├── agent.py
│   └── templates.py
├── graphviz/                # 지식 그래프 시각화 (streamlit-agraph)
│   ├── __init__.py
│   ├── agent.py
│   └── visualizer.py
├── supervisor/              # 오케스트레이션 (LangGraph, Redis Redlock)
│   ├── __init__.py
│   ├── agent.py
│   ├── workflow.py          # LangGraph 워크플로우
│   └── locks.py             # Redis Redlock
└── feedback/                # 피드백 처리 (SQLite, Slack Webhook)
    ├── __init__.py
    ├── agent.py
    └── handlers.py
```

#### src/core/ - 핵심 기능
```
src/core/
├── schemas/                 # 공통 JSON Schema
│   ├── __init__.py
│   ├── base.py              # 기본 스키마
│   ├── agents.py            # 에이전트 I/O 스키마
│   └── workflow.py          # 워크플로우 스키마
├── storage/                 # 데이터 저장소
│   ├── __init__.py
│   ├── knowledge_graph/     # RDFLib + Turtle/JSON-LD
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── models.py
│   ├── vector_store/        # FAISS IVF-HNSW (4096 dim)
│   │   ├── __init__.py
│   │   └── faiss_store.py
│   └── history/             # SQLite → TimescaleDB
│       ├── __init__.py
│       └── sqlite_store.py
├── workflow/                # LangGraph 워크플로우 정의
│   ├── __init__.py
│   ├── definitions.py       # 워크플로우 정의
│   └── checkpoints.py       # 체크포인트 관리
└── utils/                   # 공통 유틸리티
    ├── __init__.py
    ├── logging.py           # 구조화된 로깅
    ├── metrics.py           # 성능 메트릭
    └── validators.py        # 공통 검증 로직
```

#### src/api/ - REST API (FastAPI)
```
src/api/
├── __init__.py
├── main.py                  # FastAPI 앱
├── routes/                  # API 엔드포인트
│   ├── __init__.py
│   ├── agents.py            # 에이전트 API
│   ├── workflow.py          # 워크플로우 API
│   └── health.py            # 헬스체크
└── middleware/              # 미들웨어
    ├── __init__.py
    ├── auth.py              # 인증
    ├── logging.py           # 로깅
    └── cors.py              # CORS
```

#### src/ui/ - Streamlit UI
```
src/ui/
├── __init__.py
├── main.py                  # Streamlit 앱
├── pages/                   # UI 페이지
│   ├── __init__.py
│   ├── graph.py             # 그래프 시각화 페이지
│   ├── wiki.py              # 위키 편집 페이지
│   └── feedback.py          # 피드백 페이지
└── components/              # 재사용 컴포넌트
    ├── __init__.py
    ├── graph_viz.py         # 그래프 시각화 컴포넌트
    └── wiki_editor.py       # 위키 에디터 컴포넌트
```

#### config/ - 설정 관리
```
config/
├── environments/            # 환경별 설정
│   ├── __init__.py
│   ├── development.py       # 개발 환경
│   ├── production.py        # 운영 환경
│   └── testing.py           # 테스트 환경
├── templates/               # Jinja2 템플릿
│   ├── wiki/               # 위키 템플릿
│   └── prompts/            # 프롬프트 템플릿
└── settings.py              # 설정 로더
```

#### tests/ - 테스트 구조
```
tests/
├── unit/                    # 단위 테스트
│   ├── agents/              # 에이전트 단위 테스트
│   ├── core/                # 핵심 기능 단위 테스트
│   ├── api/                 # API 단위 테스트
│   └── ui/                  # UI 단위 테스트
├── integration/             # 통합 테스트
│   ├── agents/              # 에이전트 통합 테스트
│   ├── workflow/            # 워크플로우 통합 테스트
│   └── api/                 # API 통합 테스트
├── performance/             # 성능 테스트
│   ├── agents/              # 에이전트 성능 테스트
│   └── workflow/            # 워크플로우 성능 테스트
├── e2e/                     # 엔드투엔드 테스트
│   ├── scenarios/           # 시나리오별 테스트
│   └── fixtures/            # 테스트 픽스처
└── conftest.py              # pytest 설정
```

#### docs/ - 문서
```
docs/
├── api/                     # API 문서
│   ├── endpoints.md         # 엔드포인트 문서
│   └── schemas.md           # 스키마 문서
├── deployment/              # 배포 가이드
│   ├── docker.md            # Docker 배포
│   ├── kubernetes.md        # Kubernetes 배포
│   └── terraform.md         # Terraform 인프라
├── user_guide/              # 사용자 가이드
│   ├── getting_started.md   # 시작 가이드
│   ├── agents.md            # 에이전트 사용법
│   └── troubleshooting.md   # 문제 해결
└── architecture/            # 아키텍처 문서
    ├── overview.md          # 전체 아키텍처
    ├── agents.md            # 에이전트 아키텍처
    └── workflow.md          # 워크플로우 아키텍처
```

## 3. 마이그레이션 매핑

### 3.1 파일 이동 매핑
| 현재 경로 | 새 경로 | 비고 |
|----------|---------|------|
| `server/agents/research/*` | `src/agents/research/*` | Research Agent |
| `server/agents/extractor/*` | `src/agents/extractor/*` | Extractor Agent |
| `server/agents/retriever/*` | `src/agents/retriever/*` | Retriever Agent |
| `server/agents/wiki/*` | `src/agents/wiki/*` | Wiki Agent |
| `server/agents/graphviz/*` | `src/agents/graphviz/*` | GraphViz Agent |
| `server/agents/supervisor/*` | `src/agents/supervisor/*` | Supervisor Agent |
| `server/agents/feedback/*` | `src/agents/feedback/*` | Feedback Agent |
| `server/schemas/*` | `src/core/schemas/*` | 공통 스키마 |
| `server/utils/*` | `src/core/utils/*` | 공통 유틸리티 |
| `server/workflow/*` | `src/core/workflow/*` | 워크플로우 |
| `server/retrieval/*` | `src/core/storage/vector_store/*` | 벡터 스토어 |
| `server/routers/*` | `src/api/routes/*` | API 라우터 |
| `server/main.py` | `src/api/main.py` | FastAPI 앱 |
| `app/*` | `src/ui/*` | Streamlit UI |
| `tests/*` | `tests/*` | 구조 개선 |
| `config/*` | `config/*` | 기존 유지, 확장 |
| `docs/*` | `docs/*` | 기존 유지, 확장 |

### 3.2 Import 경로 변경
- `from server.agents.research` → `from src.agents.research`
- `from server.schemas` → `from src.core.schemas`
- `from server.utils` → `from src.core.utils`
- `from app` → `from src.ui`

## 4. 워크플로우 반영

### 4.1 PRD 워크플로우
```
Research → (Extractor ∥ Retriever) → Wiki → GraphViz
     ↓
Supervisor (LangGraph + Redis Redlock)
     ↓
Feedback (Human-in-Loop)
```

### 4.2 구조적 반영
- `src/agents/` 하위에 각 에이전트가 독립적인 패키지로 구성
- `src/core/workflow/` 에서 LangGraph 워크플로우 정의
- `src/core/storage/` 에서 데이터 저장소 통합 관리

## 5. Phase별 개발 고려사항

### 5.1 Phase 0 (Foundations)
- Research & Extractor 기본 구조
- 기본 UI 및 API

### 5.2 Phase 1 (Core RAG & Wiki)
- FAISS Store, Retriever, Wiki Agent
- Supervisor 통합

### 5.3 Phase 2 (Feedback & Security)
- Feedback Agent, OAuth2
- 그래프 편집 UI

### 5.4 Phase 3 (Scale & i18n)
- RDFLib 최적화
- 다국어 지원

## 6. 위험 요소 및 대응 방안

| 위험 요소 | 대응 방안 |
|----------|----------|
| 기능 손실 | 점진적 마이그레이션 + 각 단계별 테스트 |
| Import 오류 | 자동화된 경로 수정 스크립트 |
| CI/CD 실패 | Dockerfile 경로 업데이트 |
| 개발 지연 | Phase별 롤백 계획 |

## 7. 기대 효과

1. **개발 효율성**: 에이전트별 독립적 개발 가능
2. **확장성**: 새로운 에이전트 추가 용이
3. **유지보수성**: 관련 코드들이 논리적으로 그룹화
4. **테스트 용이성**: 구조화된 테스트 환경
5. **배포 안정성**: Phase별 독립 배포 가능

---

**작성일**: 2025-08-07  
**작성자**: AI Assistant  
**버전**: 1.0
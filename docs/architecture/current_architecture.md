# 현재 아키텍처 문서

## 개요

AI Knowledge Graph System은 새로운 `src` 구조로 리팩토링되어 모듈화되고 확장 가능한 아키텍처를 갖추게 되었습니다.

## 새로운 디렉토리 구조 (단순화 반영)

```
src/
├── core/                    # 핵심 모듈
│   ├── schemas/            # Pydantic 스키마 정의
│   │   ├── base.py        # 기본 스키마 (WorkflowState, CheckpointData 등)
│   │   └── agents.py      # 에이전트 입출력 스키마
│   ├── storage/           # 데이터 저장소
│   │   ├── database.py    # SQLAlchemy 데이터베이스 설정
│   │   ├── models.py      # ORM 모델
│   │   ├── schemas.py     # 데이터베이스 스키마
│   │   └── vector_store/  # FAISS 벡터 저장소
│   ├── utils/             # 유틸리티 함수
│   │   ├── cache_manager.py      # 캐시 관리 (diskcache 기반)
│   │   ├── config.py             # 설정 관리
│   │   ├── kg_manager.py         # RDFLib 지식 그래프 관리
│   │   ├── lock_manager.py       # 파일 기반 락 (filelock)
│   │   ├── retry_manager.py      # 고정 지연 재시도(기본 1초, 최대 3회)
│   │   ├── checkpoint_manager.py # 상태 체크포인트 및 롤백
│   │   ├── scheduler.py          # 작업 스케줄러
│   │   └── storage_manager.py    # 통합 스토리지 관리
│   └── workflow/          # 워크플로우 로직
│       ├── agents/        # 워크플로우 에이전트
│       ├── graph.py       # LangGraph 워크플로우 정의
│       └── state.py       # 워크플로우 상태 관리
├── agents/                 # AI 에이전트
│   ├── research/          # 정보 수집 에이전트
│   │   ├── agent.py       # 메인 에이전트 클래스
│   │   ├── client.py      # DuckDuckGo 클라이언트
│   │   └── cache.py       # 검색 결과 캐시
│   ├── extractor/         # 엔티티·관계 추출 에이전트
│   │   └── agent.py       # spaCy NER + korre 관계 추출 + LangGraph 워크플로우
│   ├── retriever/         # 벡터 검색 에이전트
│   │   └── agent.py       # FAISS 기반 검색
│   ├── wiki/              # 위키 생성 에이전트
│   │   ├── agent.py       # 위키 생성 로직
│   │   └── templates/     # Jinja2 템플릿
│   ├── graphviz/          # 그래프 시각화 에이전트
│   │   └── agent.py       # Streamlit 그래프 생성
│   ├── supervisor/        # 워크플로우 관리 에이전트
│   │   └── agent.py       # LangGraph 오케스트레이션(연결: filelock, retry, checkpoint)
│   └── feedback/          # 피드백 처리 에이전트
│       └── agent.py       # SQLite 기반 피드백 저장
└── api/                    # FastAPI 백엔드
    ├── routes/            # API 라우터
    │   ├── workflow.py    # 워크플로우 엔드포인트
    │   ├── checkpoints.py # 체크포인트 엔드포인트
    │   ├── retriever.py   # 검색 엔드포인트
    │   └── history.py     # 히스토리 엔드포인트
    └── main.py            # FastAPI 애플리케이션
```

## 핵심 모듈 (src/core)

### 1. 스키마 (schemas/)

Pydantic을 사용한 데이터 검증 및 직렬화를 담당합니다.

#### base.py
- `WorkflowState`: 워크플로우 상태 관리
- `CheckpointData`: 체크포인트 데이터 구조
- `MessageBase`: 메시지 기본 클래스
- `SystemStatus`: 시스템 상태 정보

#### agents.py
- 각 에이전트의 입력/출력 스키마 정의
- `ResearchIn/ResearchOut`, `ExtractorIn/ExtractorOut` 등

### 2. 스토리지 (storage/)

데이터 지속성을 담당하는 모듈들입니다.

#### database.py
- SQLAlchemy 설정 및 세션 관리
- 데이터베이스 연결 및 초기화

#### models.py
- ORM 모델 정의
- 테이블 구조 및 관계 정의

#### vector_store/
- FAISS 벡터 저장소 구현
- IVF-HNSW 인덱스 관리
- 벡터 검색 및 유사도 계산

### 3. 유틸리티 (utils/)

공통 기능을 제공하는 유틸리티 모듈들입니다.

#### cache_manager.py
- diskcache 기반 캐시 관리
- LRU 캐시 및 TTL 지원
- JSON 직렬화/역직렬화

#### lock_manager.py
- 분산 락 관리
- 파일 기반 락 구현
- 데드락 방지 및 타임아웃 처리

#### storage_manager.py
- 통합 스토리지 관리
- 체크포인트 및 워크플로우 상태 저장
- Redis 호환 인터페이스

### 4. 워크플로우 (workflow/)

LangGraph 기반 워크플로우 오케스트레이션을 담당합니다.

#### agents/
- 워크플로우 내부 에이전트 구현
- `Agent`, `ConAgent`, `JudgeAgent` 등

#### graph.py
- LangGraph 워크플로우 정의
- 노드 간 연결 및 조건부 분기

#### state.py
- 워크플로우 상태 관리
- `DebateState` 클래스

## AI 에이전트 (src/agents) — 단순화 계획 반영

### 1. Research Agent
- **역할**: 키워드 기반 문서 수집
- **기술**: DuckDuckGo API, LRU 캐시
- **입력**: 키워드, 언어, 문서 수
- **출력**: 수집된 문서 목록

### 2. Extractor Agent
- **역할**: 엔티티 및 관계 추출
- **기술**: spaCy NER, 규칙/의존구문 기반 후처리
- **입력**: 문서 목록, 추출 모드
- **출력**: 엔티티 및 관계 목록

### 3. Retriever Agent
- **역할**: 유사 문서 검색 (RAG)
- **기술**: FAISS IVF-HNSW, sentence-transformers
- **입력**: 쿼리, 유사도 임계값
- **출력**: 관련 문서 목록

### 4. Wiki Agent
- **역할**: 위키 문서 생성
- **기술**: Jinja2 템플릿, GPT-4o 스타일링
- **입력**: 엔티티, 관계, 문서
- **출력**: Markdown 위키 문서

### 5. GraphViz Agent
- **역할**: 지식 그래프 시각화
- **기술**: streamlit-agraph, st-link-analysis
- **입력**: 엔티티 및 관계 데이터
- **출력**: 인터랙티브 그래프

### 6. Supervisor Agent
- **역할**: 워크플로우 오케스트레이션
- **기술**: LangGraph, filelock, RetryManager, CheckpointManager
- **입력**: 워크플로우 정의
- **출력**: 실행 상태 및 결과

### 7. Feedback Agent
- **역할**: 사용자 피드백 처리
- **기술**: SQLite, (Slack 제거), 콘솔/파일 로깅
- **입력**: 피드백 데이터
- **출력**: 처리 결과 및 알림

## API 레이어 (src/api)

### 1. 라우터 (routes/)
- **workflow.py**: 워크플로우 시작/상태/결과 조회
- **checkpoints.py**: 체크포인트 생성/조회
- **retriever.py**: 벡터 검색
- **history.py**: 워크플로우 히스토리

### 2. 메인 애플리케이션 (main.py)
- FastAPI 애플리케이션 설정
- 미들웨어 및 라우터 등록
- CORS 및 예외 처리

## 데이터 흐름

### 1. 워크플로우 실행
```
사용자 요청 → API → Supervisor Agent → Research Agent → Extractor Agent → 
Retriever Agent → Wiki Agent → GraphViz Agent → 결과 반환
```

### 2. 데이터 저장
```
에이전트 결과 → Storage Manager → Cache Manager → 
Vector Store (FAISS) → Database (SQLite) → 지식 그래프 (RDFLib)
```

### 3. 상태 관리
```
워크플로우 상태 → WorkflowState → CheckpointData → 
Storage Manager → 파일 시스템
```

## 기술 스택

### 백엔드
- **FastAPI**: 고성능 API 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Pydantic**: 데이터 검증 및 직렬화
- **LangGraph**: 워크플로우 오케스트레이션

### AI/ML
- **Azure OpenAI GPT-4o**: 자연어 처리
- **FAISS**: 벡터 검색
- **sentence-transformers**: 텍스트 임베딩
- **RDFLib**: 지식 그래프 관리

### 스토리지
- **SQLite**: 관계형 데이터베이스
- **diskcache**: 캐시 저장소
- **FAISS**: 벡터 저장소
- **RDFLib**: RDF 그래프 저장소

### 프론트엔드
- **Streamlit**: 웹 인터페이스
- **streamlit-agraph**: 그래프 시각화

## 확장성 고려사항

### 1. 모듈화
- 각 에이전트는 독립적인 모듈로 구현
- 공통 인터페이스 (`process`, `health_check`) 정의
- 의존성 주입을 통한 결합도 감소

### 2. 확장 가능한 스토리지
- Redis에서 diskcache로 마이그레이션 완료
- 다양한 백엔드 지원 가능한 구조
- 플러그인 방식의 스토리지 어댑터

### 3. 워크플로우 유연성
- LangGraph를 통한 동적 워크플로우 구성
- 조건부 분기 및 병렬 처리 지원
- 새로운 에이전트 추가 용이

### 4. API 설계
- RESTful API 설계 원칙 준수
- 일관된 에러 처리 및 응답 형식
- 버전 관리 및 하위 호환성 고려

## 성능 최적화

### 1. 캐싱 전략
- 검색 결과 LRU 캐시
- 벡터 임베딩 캐시
- 워크플로우 상태 캐시

### 2. 비동기 처리
- FastAPI의 비동기 지원
- 에이전트 간 비동기 통신
- 백그라운드 작업 처리

### 3. 벡터 검색 최적화
- FAISS IVF-HNSW 인덱스
- 배치 처리 지원
- 메모리 효율적인 벡터 저장

## 보안 고려사항

### 1. API 보안
- 입력 데이터 검증 (Pydantic)
- SQL 인젝션 방지 (SQLAlchemy)
- CORS 설정

### 2. 데이터 보안
- 민감 정보 암호화
- 접근 권한 관리
- 감사 로그 기록

## 모니터링 및 로깅

### 1. 구조화된 로깅
- JSON 형식 로그
- 로그 레벨 관리
- 컨텍스트 정보 포함

### 2. 성능 모니터링
- 워크플로우 실행 시간 측정
- 에이전트별 성능 지표
- 시스템 리소스 모니터링

### 3. 헬스 체크
- 각 컴포넌트별 상태 확인
- 의존성 서비스 모니터링
- 자동 복구 메커니즘

이 아키텍처는 확장성, 유지보수성, 성능을 모두 고려하여 설계되었으며, 새로운 요구사항에 유연하게 대응할 수 있는 구조를 갖추고 있습니다. 
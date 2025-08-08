# 🤖 AI Knowledge Graph System

> **멀티‑에이전트 아키텍처를 활용한 키워드 기반 지식 그래프 자동 구축 및 위키 시스템**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.24+-red.svg)](https://streamlit.io/)
[![Coverage](https://img.shields.io/badge/coverage-80%25+-brightgreen.svg)](https://pytest.org/)

## 🎯 프로젝트 개요

이 시스템은 **여러 전문 AI 에이전트**가 협력하여 키워드를 기반으로 **지식 그래프를 자동으로 구축**하고, 이를 바탕으로 **위키 문서를 실시간으로 생성·편집**할 수 있는 통합 플랫폼입니다. 최근 단순화 계획에 따라 워크플로우, 락, 재시도, 체크포인트, 알림 체계가 경량화되었습니다.

### ✨ 핵심 기능

- 🔍 **자동 정보 수집**: DuckDuckGo를 통한 실시간 웹 검색 (API 키 불필요)
- 🧠 **지능형 추출(경량화)**: spaCy NER + 규칙/의존구문 기반 관계 추출  
- 📊 **벡터 검색**: FAISS IVF-HNSW 인덱스 기반 유사 문서 검색
- 📝 **위키 생성**: Jinja2 템플릿 + GPT-4o 스타일링
- 🕸️ **그래프 시각화**: streamlit-agraph 기반 인터랙티브 그래프
- 🔄 **워크플로우 관리(단순화)**: LangGraph + filelock 락 + RetryManager(고정 지연) + CheckpointManager(롤백)
- 💬 **피드백 루프(단순화)**: SQLite 저장 + 콘솔/파일 로깅 (Slack 제거)

## 🏗️ 아키텍처

### 에이전트 구성

| 에이전트 | 역할 | 주요 기술 |
|---------|------|-----------|
| **Research** | 키워드 기반 문서 수집·캐싱 | DuckDuckGo API, LRU Cache |
| **Extractor** | 엔티티·관계 추출·증분 업데이트 | spaCy NER, 규칙/의존구문 기반 후처리 |
| **Retriever** | 유사 문서 선별·문맥 보강 (RAG) | FAISS IVF‑HNSW, sentence-transformers |
| **Wiki** | Markdown 위키 작성·요약 | Jinja2 Template, GPT‑4o Styler |
| **GraphViz** | 지식 그래프 시각화 | streamlit‑agraph, st‑link‑analysis |
| **Supervisor** | 오케스트레이션·Lock·Retry | LangGraph, filelock, RetryManager, CheckpointManager |
| **Feedback** | 사용자 피드백 수집·정제 루프 | SQLite Store, (Slack 제거) |

### 기술 스택

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: Streamlit, streamlit-agraph
- **AI/LLM**: spaCy, LangChain, LangGraph (LLM 선택사항)
- **Database/Storage**: RDFLib + SQLite (지식 그래프), diskcache (캐시)
- **Vector Store**: FAISS IVF-HNSW (4096차원)
- **Infrastructure**: Docker, Docker Compose
- **Testing**: pytest (≥80% 커버리지), pytest-cov

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 리포지토리 클론
git clone <repository-url>
cd final

# 환경변수 설정
cp config/environment.template .env
# .env 파일을 편집하여 필수 값들을 설정하세요
```

### 2. 필수 환경변수

```bash
# Azure OpenAI (필수)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOY_GPT4O=your_gpt4o_deployment

# 검색 API (선택)
# SERPAPI_KEY=your_serpapi_key  # SerpAPI 제거 (DuckDuckGo만 사용)

# 데이터베이스/스토리지 (Docker 사용 시 기본값)
RDFLIB_STORE_URI=sqlite:///./data/kg.db
API_BASE_URL=http://localhost:8000/api/v1
```

### 3. Docker로 시작 (권장)

```bash
# 전체 시스템 시작
make docker-up

# 또는 개발 도구 포함
make docker-up-dev

# 서비스 확인
make docker-logs
```

### 4. 로컬 개발 환경

```bash
# 개발 환경 설정
make dev-setup

# 의존성 설치
make install-dev

# 테스트 실행
make test

# 서비스 개별 시작
# Terminal 1: FastAPI
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Streamlit
API_BASE_URL=http://localhost:8000/api/v1 streamlit run app/main.py
```

## 🌐 서비스 접근

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Streamlit UI** | http://localhost:8501 | 메인 사용자 인터페이스 |
| **FastAPI Backend** | http://localhost:8000 | REST API 서버 |
| **API 문서** | http://localhost:8000/docs | Swagger UI |
| **RDFLib Graph** | ./data/kg.db | 지식 그래프 데이터 |

## 📁 프로젝트 구조

```
final/
├── src/                         # 소스 코드 (새로운 구조)
│   ├── core/                   # 핵심 모듈
│   │   ├── schemas/           # Pydantic 스키마
│   │   ├── storage/           # 데이터베이스 및 스토리지
│   │   ├── utils/             # 유틸리티 함수
│   │   └── workflow/          # 워크플로우 로직
│   ├── agents/                 # 7개 AI 에이전트
│   │   ├── research/          # 정보 수집 에이전트
│   │   ├── extractor/         # 엔티티 추출 에이전트
│   │   ├── retriever/         # RAG 검색 에이전트
│   │   ├── wiki/              # 위키 생성 에이전트
│   │   ├── graphviz/          # 그래프 시각화 에이전트
│   │   ├── supervisor/        # 워크플로우 관리 에이전트
│   │   └── feedback/          # 피드백 처리 에이전트
│   └── api/                    # FastAPI 백엔드
│       ├── routes/            # API 라우터
│       └── main.py            # FastAPI 앱
├── app/                        # Streamlit 프론트엔드
│   ├── components/             # UI 컴포넌트
│   ├── utils/                 # 유틸리티 함수
│   └── main.py                # 메인 앱
├── tests/                      # 테스트 코드
│   ├── unit/                  # 단위 테스트
│   ├── integration/           # 통합 테스트
│   ├── e2e/                   # E2E 테스트
│   └── agents/                # 에이전트별 테스트
├── infra/                     # 인프라 설정
│   └── docker-compose.yml     # Docker 구성
├── config/                    # 설정 파일
├── prompts/                   # AI 프롬프트 템플릿
├── data/                      # 데이터 저장소
└── run_api.py                 # API 서버 실행 스크립트
```

## 🧪 테스트

이 프로젝트는 단순화된 구조에 맞춰 **최소 커버리지 25% (점진 상향 예정)**를 기준으로 합니다.

```bash
# 전체 테스트 실행
make test

# 카테고리별 테스트
make test-unit          # 단위 테스트
make test-integration   # 통합 테스트  
make test-e2e          # E2E 테스트
make test-agents       # 에이전트 테스트

# 커버리지 리포트
make test-coverage

# 빠른 테스트 (slow 제외)
make test-fast
```

## 🔧 개발 도구

```bash
# 코드 포맷팅
make format

# 린팅
make lint

# 전체 CI 검사 (포맷팅 + 린팅 + 테스트)
make ci-test

# 환경 정리
make clean
```

## 📊 사용 시나리오

### 1. 연구자/데이터 분석가
- 특정 주제에 대한 포괄적 지식 그래프 구축
- 최신 연구 동향 및 관련 논문 자동 수집
- 시각적 지식 맵을 통한 인사이트 발견

### 2. 콘텐츠 에디터
- 주제별 위키 문서 자동 생성 및 편집
- 실시간 정보 업데이트 및 검증
- 협업 기반 콘텐츠 품질 관리

### 3. 일반 사용자
- 관심 주제에 대한 구조화된 정보 탐색
- 인터랙티브 그래프를 통한 직관적 학습
- 개인화된 지식 베이스 구축

## 🔄 워크플로우

1. **키워드 입력** → Research Agent가 관련 문서 수집
2. **정보 추출** → Extractor Agent가 엔티티·관계 추출  
3. **유사도 검색** → Retriever Agent가 관련 문서 선별
4. **위키 생성** → Wiki Agent가 Markdown 문서 작성
5. **그래프 시각화** → GraphViz Agent가 인터랙티브 그래프 생성
6. **전체 관리** → Supervisor Agent가 워크플로우 오케스트레이션
7. **피드백 처리** → Feedback Agent가 사용자 입력 반영

## 🛡️ 보안 & 인증

- **JWT 기반 인증**: 안전한 사용자 세션 관리
- **OAuth2 프록시**: 외부 인증 제공자 연동
- **RBAC**: 역할 기반 접근 제어
- **API Rate Limiting**: API 남용 방지

## 📈 모니터링 & 알림(단순화)

- **구조화된 로깅**: 콘솔/파일 로깅 중심 (Slack 제거)
- **헬스체크**: 서비스 상태 실시간 확인

## 🤝 기여 방법

1. 이 리포지토리를 Fork
2. 새 기능 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

### 개발 가이드라인

- **테스트**: 새 기능에는 반드시 테스트 추가
- **커버리지**: 80% 이상 유지
- **코드 품질**: `make lint`와 `make format` 통과
- **문서화**: README 및 코드 주석 업데이트

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- [LangChain](https://langchain.com/) - 워크플로우 오케스트레이션
- [Streamlit](https://streamlit.io/) - 빠른 UI 개발
- [FastAPI](https://fastapi.tiangolo.com/) - 고성능 API 프레임워크
- [RDFLib](https://rdflib.readthedocs.io/) - RDF 그래프 라이브러리
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - AI 모델 서비스

## 📞 문의 및 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **문서**: [Wiki](https://github.com/your-repo/wiki)

---

<div align="center">
  <strong>🚀 지식의 미래를 함께 만들어가세요! 🚀</strong>
</div>
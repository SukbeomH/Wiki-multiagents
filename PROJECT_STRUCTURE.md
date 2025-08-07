# 프로젝트 구조

## 현재 구조 (PRD 기준 정리 완료)

```
final/
├── app/                          # Streamlit UI
│   ├── components/
│   │   ├── history.py
│   │   └── sidebar.py
│   ├── utils/
│   │   └── state_manager.py
│   ├── main.py
│   └── Dockerfile
├── server/                       # FastAPI Backend
│   ├── agents/                   # 7개 에이전트 (PRD 기준)
│   │   ├── research/            # 키워드 기반 문서 수집·캐싱
│   │   ├── extractor/           # 엔티티·관계 추출·증분 업데이트
│   │   ├── retriever/           # 유사 문서 선별·문맥 보강 (RAG)
│   │   ├── wiki/                # Markdown 위키 작성·요약
│   │   ├── graphviz/            # 지식 그래프 시각화
│   │   ├── supervisor/          # 오케스트레이션·Lock·Retry
│   │   └── feedback/            # 사용자 피드백 수집·정제 루프
│   ├── db/                      # 데이터베이스 관련
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── retrieval/               # 검색 서비스
│   │   ├── search_service.py
│   │   └── vector_store.py
│   ├── routers/                 # API 라우터
│   │   ├── history.py
│   │   └── workflow.py
│   ├── utils/                   # 유틸리티
│   │   └── config.py
│   ├── workflow/               # 워크플로우 (기존)
│   │   ├── agents/
│   │   ├── graph.py
│   │   └── state.py
│   ├── main.py
│   └── Dockerfile
├── infra/                       # 인프라 설정
│   └── docker-compose.yml       # 실제 구성 파일
├── tests/                       # 테스트 파일
├── prompts/                     # AI 프롬프트 템플릿
│   └── README.md
├── config/                      # 설정 파일
│   ├── environment.template     # 환경변수 템플릿
│   └── README.md               # 설정 가이드
├── data/                        # 데이터 저장소 (FAISS 인덱스 등)
├── scripts/                     # 스크립트
│   └── PRD.txt
├── requirements.txt
├── docker-compose.yml          # 메인 Compose 파일 (infra 참조)
├── .dockerignore
└── PROJECT_STRUCTURE.md        # 이 파일
```

## 다음 단계

1. ✅ 디렉토리 구조 정리 완료
2. 🔄 requirements.txt 확장 (RDFLib, Redis, FAISS 등)
3. 🔄 pytest 설정 및 기본 테스트 구조 생성
4. 🔄 README.md 업데이트 (PRD 목표에 맞게)
5. 🔄 GitHub Actions CI 워크플로우 설정

## 서비스 포트

- Streamlit UI: http://localhost:8501
- FastAPI Backend: http://localhost:8000
- RDFLib Storage: File-based SQLite storage
- Redis: localhost:6379
- Redis Commander: http://localhost:8081 (dev 프로필)

## 시작하기

```bash
# 1. 환경변수 설정
cp config/environment.template .env
# .env 파일 편집

# 2. 전체 시스템 시작
docker-compose up -d

# 3. 개발 도구 포함 시작
docker-compose --profile dev up -d
```
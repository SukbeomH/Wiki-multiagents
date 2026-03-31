# Architecture — AI 한국은행 경제 분석팀

> Multi-agent AI 시스템 (LangChain/LangGraph 기반 Streamlit 웹앱)

## 프로젝트 개요

경제 분석 전문 멀티 에이전트 시스템. RAG(Retrieval-Augmented Generation)와 실시간 웹 검색을 결합하여 경제 질문에 심층 답변 제공.

## 디렉토리 구조

```
├── app.py                          # 메인 Streamlit 앱 (644줄)
├── pages/                          # 멀티페이지 뷰
│   ├── 01_⚙️_설정.py               # 설정 & 환경 검증
│   └── 02_📖_도움말.py             # 도움말 & FAQ
├── core/                           # 핵심 비즈니스 로직
│   ├── config.py                   # 설정 관리
│   ├── logger.py                   # 로깅 시스템
│   ├── model_factory.py            # Azure OpenAI 팩토리
│   ├── rag_pipeline.py             # RAG/벡터 검색
│   ├── web_search.py               # 웹 검색 (DDGS)
│   └── state_manager.py            # 세션 상태 관리
├── components/                     # 재사용 UI 컴포넌트
│   ├── sidebar.py                  # 사이드바 (PDF 업로드)
│   ├── chat_interface.py           # 채팅 메시지 & 근거 미리보기
│   └── common.py                   # 공통 UI 유틸리티
├── utils/                          # 유틸리티
│   ├── env_validator.py            # 환경 검증
│   └── helpers.py                  # 텍스트 처리 & 소스 추출
└── data/                           # 데이터 (PDF, FAISS 인덱스)
```

## 에이전트 시스템 (LangGraph)

### Supervisor Agent (라우터)
- 워크플로우 오케스트레이션
- 라우팅: `researcher` | `analyst` | `END`

### Researcher Agent (도구 사용)
- FAISS 벡터 인덱스 + 웹 검색
- 도구: `bok_document_search`, `web_search`, `relaxed_document_search`
- 2단계 검색: 기본 + relaxed 폴백

### Analyst Agent (분석)
- Researcher 출력 기반 심층 경제 분석
- 근거 참조 포함 구조화된 답변

## 워크플로우

```
START (Supervisor) → [조건부 라우팅]
  ├→ Researcher (도구 실행) → Supervisor로 복귀
  ├→ Analyst (최종 답변) → END
  └→ END (직접 종료)
```

## 데이터 파이프라인

```
PDF 업로드 → PyMuPDFLoader → RecursiveCharacterTextSplitter
  → Azure OpenAI Embeddings (text-embedding-3-large)
  → FAISS Vector Store → Retriever (MMR/Similarity)
  → Optional: LLMChainExtractor (컨텍스트 압축)
```

## 주요 패턴

| 패턴 | 구현 |
|------|------|
| Factory | AzureModelFactory (LLM/임베딩 인스턴스) |
| Singleton | 모델 인스턴스 캐싱 |
| State Management | StateManager (세션 상태 중앙 관리) |
| Conditional Routing | Supervisor 텍스트 기반 라우팅 |
| Caching | FAISS 인덱스 + 모델 인스턴스 + 그래프 캐싱 |

---

*Last updated: 2026-03-31*

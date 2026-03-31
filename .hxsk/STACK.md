# Tech Stack

## 언어 & 프레임워크

| 레이어 | 기술 | 버전 |
|--------|------|------|
| Frontend | Streamlit | 1.48.0 |
| Agent Framework | LangGraph | 0.6.4 |
| | LangChain | 0.3.27 |
| | LangChain-OpenAI | 0.3.29 |
| LLM | Azure OpenAI API | GPT-4o |
| Language | Python | 3.x |

## 핵심 라이브러리

**AI/ML**: langchain-core, langgraph, langgraph-checkpoint, langchain-text-splitters, langchain-community, openai
**벡터/검색**: faiss-cpu, langchain-openai (Azure embeddings)
**웹 검색**: ddgs (DuckDuckGo)
**문서 처리**: pymupdf, lxml
**데이터**: pandas, numpy, pyarrow, sqlalchemy
**HTTP**: httpx, aiohttp, requests
**설정**: python-dotenv, pydantic-settings

## 패키지 매니저

- **Primary**: uv
- **Fallback**: pip

## 필수 환경 변수

```
AOAI_ENDPOINT              # Azure OpenAI 엔드포인트
AOAI_API_KEY               # Azure OpenAI API 키
AOAI_DEPLOY_GPT4O          # GPT-4o 배포명
AOAI_DEPLOY_EMBED_3_LARGE  # 임베딩 모델 배포명
```

## 통계

- 소스 코드: ~3,500+ 줄
- 핵심 모듈: 6개 (core/)
- UI 컴포넌트: 3개 (components/)
- 의존성 패키지: ~90개
- 에이전트: 3개 (Supervisor, Researcher, Analyst)

---

*Last updated: 2026-03-31*

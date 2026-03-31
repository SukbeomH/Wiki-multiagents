# REPORT-001: 제작 의도 및 현재 구현 상태 분석

> **작성일**: 2026-03-31
> **분석 대상**: AI 한국은행 경제 분석팀 (Wiki-multiagents)
> **브랜치**: SukbeomH/setup

---

## 1. 제작 의도

### 1.1 비전

LangGraph 기반 멀티에이전트 협업 시스템으로, 금융 전문가/연구자/학생이 한국은행 PDF 문서와 실시간 웹 정보를 결합하여 **심층 경제 분석**을 수행할 수 있는 대화형 도구.

### 1.2 핵심 목표 (PRD 기준)

| 목표 | 설명 |
|------|------|
| 멀티에이전트 협업 분석 | Supervisor가 질문을 해석하고 Researcher/Analyst에게 동적 분배 |
| 동적 RAG 소스 관리 | PDF 업로드 시 실시간 파이프라인 갱신, 파일 변경 감지 자동 캐시 리셋 |
| 실시간 프로세스 시각화 | Streamlit 네이티브 컴포넌트로 "조사 중", "분석 중" 등 상태 표시 |
| 접근성 높은 UI/UX | 직관적 채팅 + 업로드 인터페이스, 근거 미리보기 |

### 1.3 타겟 사용자

- **금융 애널리스트**: 한국은행 보고서 기반 심층 분석
- **경제학 대학원생**: 연구 자료 조사 및 인사이트 도출
- **경제 기자**: 최신 경제 동향 빠른 파악

### 1.4 기술 선택 근거

| 기술 | 선택 이유 |
|------|----------|
| Azure OpenAI (GPT-4o) | 기업 환경 호환, 높은 분석 품질 |
| LangGraph | 조건부 라우팅, 상태 기반 멀티에이전트 오케스트레이션 |
| FAISS | 인메모리 벡터 검색, 동적 재생성 용이 |
| Streamlit | 빠른 프로토타이핑, 네이티브 채팅 컴포넌트 |
| DDGS | 외부 API 키 없이 웹 검색 가능 |

---

## 2. 프로젝트 진화 과정

### Phase 1: 엔터프라이즈 시스템 (2025.08)

초기에는 **FastAPI 백엔드 + Streamlit 프론트엔드** 이중 구조:
- Redis 분산 캐싱
- SQLite 지식 그래프 (RDFLib)
- 피드백 에이전트 시스템
- Docker/K8s 인프라
- CI/CD 파이프라인, 테스트 스위트

### Phase 2: 단순화 (2025.09~10)

`단순화 계획` 커밋을 기점으로 체계적 복잡성 제거:
- FastAPI 서버 삭제
- Docker/Makefile/GitHub Workflows 제거
- Slack 연동, 채팅 히스토리 등 부가 기능 제거
- 테스트 프레임워크 축소

### Phase 3: Streamlit 전용 (2025.11~현재)

순수 Streamlit 앱으로 전환:
- Config 클래스, ModelFactory 패턴 도입
- Supervisor 텍스트 기반 라우팅 변경
- 레거시 앱 버전 삭제 (app0.py, app_single.py)
- **v2.2**: Streamlit 네이티브 컴포넌트 전환, CSS 의존성 제거

---

## 3. 현재 구현 상태

### 3.1 아키텍처 개요

```
사용자 → Streamlit UI → LangGraph StateGraph
                              │
                         Supervisor (라우터)
                        ┌─────┼─────┐
                   Researcher  │   Analyst
                   (도구 사용)  │  (분석 전용)
                        │      │      │
                   FAISS+웹검색 │   최종 답변
                        └─────┘      │
                                    END
```

### 3.2 모듈별 구현 현황

| 모듈 | 파일 | 줄수 | 완성도 | 비고 |
|------|------|------|--------|------|
| **메인 앱** | app.py | 645 | 90% | 응답 추출 로직 복잡, 폴백 체인 취약 |
| **설정** | core/config.py | 186 | 95% | OUTPUT_FORMAT 정의됐으나 미사용 |
| **로깅** | core/logger.py | 93 | 90% | 파일 출력 없음, emit() 예외 무시 |
| **모델 팩토리** | core/model_factory.py | 54 | 85% | 스레드 안전성 미보장 |
| **RAG 파이프라인** | core/rag_pipeline.py | 267 | 85% | 폴백 더미 문서, relaxed 임계값 하드코딩 |
| **웹 검색** | core/web_search.py | 73 | 80% | SSL 검증 비활성, 백엔드 하드코딩 |
| **상태 관리** | core/state_manager.py | 156 | 95% | 안정적, 초기 메시지 하드코딩 |
| **사이드바** | components/sidebar.py | 125 | 90% | 캐시 전체 초기화 문제 |
| **채팅 UI** | components/chat_interface.py | 78 | 80% | 주석 처리된 죽은 코드 존재 |
| **공통 UI** | components/common.py | 70 | 70% | 얇은 래퍼, StateManager 미사용 import |
| **환경 검증** | utils/env_validator.py | 178 | 75% | "app_refactored.py" 잘못된 참조 |
| **헬퍼** | utils/helpers.py | 131 | 70% | recency_score 항상 5 반환, 정규식 취약 |
| **설정 페이지** | pages/01_설정.py | 202 | 85% | API 키 마스킹 불충분 |
| **도움말 페이지** | pages/02_도움말.py | 283 | 90% | 하드코딩된 콘텐츠, 유지보수 어려움 |

### 3.3 PRD 대비 구현 달성률

| PRD 요구사항 | 상태 | 상세 |
|-------------|------|------|
| 3-에이전트 협업 (Supervisor/Researcher/Analyst) | **구현됨** | LangGraph StateGraph, 조건부 라우팅 |
| PDF RAG 파이프라인 | **구현됨** | FAISS + MMR/Similarity, 압축 옵션 |
| 실시간 웹 검색 | **구현됨** | DDGS 기반, 토글 on/off |
| Streamlit 채팅 UI | **구현됨** | 네이티브 컴포넌트, 멀티페이지 |
| 실시간 프로세스 시각화 | **부분 구현** | 스트리밍 있으나 단계별 상태 표시 미흡 |
| 근거 미리보기 | **구현됨** | 상위 3개 소스 expander 표시 |
| 차트 생성 에이전트 (Phase 2) | **미구현** | PRD Phase 2 항목 |
| 사용자 피드백 시스템 (Phase 2) | **미구현** | Phase 1에서 제거됨 |
| KOSIS 공공 데이터 연동 (Phase 2) | **미구현** | PRD Phase 2 항목 |
| 출처 귀속 표시 (Phase 2) | **부분 구현** | extract_source_info 있으나 불완전 |

**MVP 달성률: ~85%** — 핵심 기능 구현 완료, 안정성/품질 개선 필요

---

## 4. 주요 발견 사항

### 4.1 강점

1. **명확한 모듈 분리**: core/components/utils/pages 구조로 관심사 분리 우수
2. **설정 외부화**: Config 클래스 + .env로 25개 이상 파라미터 관리
3. **캐싱 전략**: FAISS 인덱스 디스크 저장, 모델 인스턴스 캐싱, 그래프 캐싱
4. **재시도 로직**: 에이전트 실행(3회), 웹 검색(3회) 지수 백오프 구현
5. **기술 부채 마커 없음**: TODO/FIXME/HACK 주석 0건

### 4.2 위험 요소

#### HIGH — 즉시 대응 필요

| # | 문제 | 위치 | 영향 |
|---|------|------|------|
| H1 | **응답 추출 로직 취약** | app.py:483-613 | 다단계 폴백 체인이 조건에 따라 무응답/잘못된 응답 반환 가능 |
| H2 | **Supervisor "Final Answer" 모순** | app.py:486 | 시스템 프롬프트에서 금지한 패턴을 응답 추출에서 기대 |

#### MEDIUM — 계획적 대응 필요

| # | 문제 | 위치 | 영향 |
|---|------|------|------|
| M1 | SSL 검증 비활성 | web_search.py:33 | 중간자 공격 가능성 |
| M2 | FAISS 역직렬화 취약점 | rag_pipeline.py:42 | allow_dangerous_deserialization=True |
| M3 | API 키 노출 | pages/01_설정.py:74 | 첫 10자 표시 — 마스킹 불충분 |
| M4 | Supervisor 타임아웃 관리 | app.py:179-185 | 함수 속성으로 상태 저장 — 비표준적 |
| M5 | 더미 문서 폴백 | rag_pipeline.py:217 | PDF 없을 때 가짜 문서로 검색 — 사용자 혼동 |
| M6 | 전체 캐시 초기화 | sidebar.py:103 | 파일 업로드 시 모든 st.cache_resource 삭제 |
| M7 | 스레드 안전성 | model_factory.py | 캐시 접근에 락 없음 |

#### LOW — 개선 권장

| # | 문제 | 위치 |
|---|------|------|
| L1 | recency_score 항상 5 반환 | helpers.py:98 |
| L2 | 죽은 코드 (주석 처리) | chat_interface.py:55-67 |
| L3 | 미사용 import (StateManager) | common.py:7 |
| L4 | 잘못된 파일 참조 (app_refactored.py) | env_validator.py:141 |
| L5 | OUTPUT_FORMAT 정의만 되고 미사용 | config.py:61-82 |

---

## 5. 요약 및 권장 사항

### 현재 상태 한줄 요약

> **MVP 핵심 기능은 구현 완료되었으나, 응답 추출 안정성과 보안 이슈가 프로덕션 배포 전 해결 필요.**

### 권장 다음 단계

1. **안정성 강화** (우선순위 1)
   - app.py 응답 추출 로직 단순화 및 테스트 케이스 작성
   - Supervisor 프롬프트와 파싱 로직 일관성 확보

2. **보안 개선** (우선순위 2)
   - API 키 마스킹 강화 (전체 마스킹 또는 마지막 4자만 표시)
   - SSL 검증 옵션화
   - FAISS 역직렬화 안전성 검토

3. **코드 정리** (우선순위 3)
   - 죽은 코드/미사용 import 제거
   - helpers.py recency_score 구현 또는 제거
   - env_validator.py 잘못된 참조 수정

4. **Phase 2 진입 준비**
   - SPEC.md 확정 (DRAFT → FINALIZED)
   - 차트 생성 에이전트, KOSIS 연동 등 범위 확정

---

*Last updated: 2026-03-31*

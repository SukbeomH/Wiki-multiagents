# Chat 1

## 1. 프로젝트 전체 단계별 계획 수립

* **목표**: 키워드 기반 지식 그래프 구축 + 위키 시스템
* **Option**: 기존 토론 시스템을 Phase 0으로 간주하고 단계별로 기능 확장
* **8단계 플랜**:

  1. 프로젝트 구조 평가 및 PRD 매핑
  2. Docker Compose 파일 생성 (Streamlit, FastAPI, Neo4j, Redis)
  3. `.env.example` / 환경변수 템플릿 생성
  4. 디렉토리 구조 정리 (`app/`, `server/agents/`, `infra/`, `tests/` 등)
  5. `requirements.txt` 확장 (AI/LLM, DB, Vector, Search, UI, Auth, Testing 등)
  6. `pytest` 설정 및 기본 테스트 구조 생성 (unit, integration, e2e, agent별)
  7. README 업데이트 (프로젝트 개요, 아키텍처, 빠른 시작, 테스트 가이드 등)
  8. GitHub Actions CI/CD 워크플로우 설정 (lint, type-check, unit/integration/E2E 테스트, Docker 빌드/배포, 자동 라벨링)

## 2. 환경 테스트

* **Docker 환경**: 네트워크 이슈 발생 → 로컬 Python 환경으로 대체
* **로컬 테스트**:

  * Python 3.13.5 가상환경 설정
  * 간단 FastAPI 테스트 앱 작성 (`/`, `/health`, `/env-test` 엔드포인트)
  * 주요 라이브러리(FastAPI, Streamlit, Pandas, NumPy 등) 정상 작동 확인
  * 환경변수 (Azure OpenAI, Neo4j, Redis, SerpAPI) 모두 올바르게 로드됨
* **결론**: Docker는 개선 필요, 그러나 로컬 개발 환경은 준비 완료

## 3. Task 2: 메시지 스키마 정의 준비

* **Task 2 개요**: 메시지 스키마 및 Schema Registry 구현
* **첫 번째 서브태스크 (2.1)**: Pydantic 기반 공통 메시지 및 상태 스키마 정의

  * **`MessageHeader`**: `msg_id`, `agent`, `ts`, `trace_id`, `version`
  * **`MessageBase`**: `header`, `status`, `payload`, `error_message`, `created_at`, `updated_at` + 상태 전환 메서드
  * **`WorkflowState`**: `workflow_id`, `trace_id`, `current_stage`, `keyword`, 각 단계별 완료 플래그 및 결과, 생성/수정/완료 시각, 진행률 계산
  * **`CheckpointData`**: 체크포인트 ID, 워크플로우 ID, 타입, 상태 스냅샷, 생성 시각, 보관 기한 검증
  * **`SystemStatus`**: 시스템 인스턴스 ID, 전체 상태, 워크플로우 통계, 에이전트 연결 상태, 외부 서비스 연결 상태, 마지막 헬스체크 시각, 가동 시간, 건강도 판별 메서드
* **다음 단계**: 7개 에이전트 별 Input/Output 스키마(ResearchIn/Out, ExtractorIn/Out, Entity/Relation 등)를 계속 정의

---

# Chat 2

## 1. 프로젝트 개요

* **목표**: 키워드 기반 지식 그래프 자동 구축 및 실시간 위키 생성 시스템
* **아키텍처**: 멀티-에이전트(Research, Extractor, Retriever, Wiki, GraphViz, Supervisor, Feedback) + Redis-JSON 체크포인터 + RDFLib 지식 그래프 + Streamlit UI + FastAPI 백엔드

## 2. 진행된 주요 작업

1. **환경 세팅 검증**

   * Docker 대신 로컬 Python(3.13) 환경에서 FastAPI, Streamlit, Neo4j→RDFLib 전환 테스트 완료
   * `.env` 변수 이름 불일치( `AOAI_*` vs `AZURE_OPENAI_*` ) 및 Langfuse 누락 변수 오류 수정
   * Pydantic Settings 클래스에 `extra='ignore'` 설정 추가하여 불필요 변수 무시

2. **Task 2.1: 메시지 스키마 정의**

   * Pydantic 기반 공통 메시지: `MessageHeader`, `MessageBase`, `WorkflowState`, `CheckpointData`, `SystemStatus`
   * 7개 에이전트별 Input/Output 스키마(ResearchIn/Out, ExtractorIn/Out, …, FeedbackIn/Out) 구현
   * CheckpointType Enum 및 주기·단계·수동·오류 복구 체크포인트 방식 정의

3. **문서 및 테스트 업데이트**

   * PRD(요구사항 문서) 내 Neo4j → RDFLib 반영 완료
   * `.env.example`, 환경설정 가이드, CI pytest 픽스처, E2E 통합 검증 보고서 등 문서 일관성 검토 및 수정
   * `pytest` 설정 파일과 슬랙/Redis/SQLite mock 픽스처에 Neo4j 관련 내용 제거

## 3. 현재 상태

* **설정 파일**: 정상 로드 및 LLM·임베딩·Redis 구성 함수 검증 완료
* **메시지 스키마**: Pydantic 모델 완성, E2E 테스트 통과
* **문서**: PRD, 가이드, 인프라·배포 스크립트, README 등 Neo4j→RDFLib 변경 사항 반영 완료
* **테스트**: 단위·통합·E2E 모두 성공

## 4. 다음 단계

* **Task 2.2\~2.5**:

  * Redis-JSON Snapshot 시스템 구현 및 검증
  * Checkpointer API(Rest 엔드포인트) 완전 구현
  * 인프라 자동화(Docker Compose, Terraform) 완전 배포
  * 종합 통합 검증 및 보고서 완성
* 이후 **Task 3.x**: 실제 AI 에이전트 구현 및 지식그래프 생성 로직 개발

---


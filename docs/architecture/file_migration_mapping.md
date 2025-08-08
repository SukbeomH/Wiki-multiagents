# 파일 마이그레이션 매핑 가이드

## 개요

이 문서는 기존 프로젝트 구조에서 새로운 `src/` 기반 구조로의 파일 마이그레이션 매핑을 정의합니다.

## 마이그레이션 원칙

1. **기능별 그룹화**: 관련 기능을 논리적으로 그룹화
2. **의존성 최소화**: 순환 의존성 방지
3. **확장성 고려**: 새로운 에이전트/기능 추가 용이성
4. **테스트 구조 개선**: 단위/통합/성능/E2E 테스트 분리

## 1. 에이전트 파일 마이그레이션

### 1.1 Research Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/research/agent.py` | `src/agents/research/agent.py` | ✅ 완료 | 메인 Research Agent |
| `server/agents/research/client.py` | `src/agents/research/client.py` | ✅ 완료 | DuckDuckGo API 클라이언트 |
| `server/agents/research/cache.py` | `src/agents/research/cache.py` | ✅ 완료 | 캐싱 시스템 |
| `server/agents/research/config.py` | `src/agents/research/config.py` | ✅ 완료 | 성능 설정 |
| `server/agents/research/__init__.py` | `src/agents/research/__init__.py` | ✅ 완료 | 패키지 초기화 |
| `server/agents/research/research_agent.py.backup` | 삭제 예정 | ⏳ 대기 | 백업 파일 |

### 1.2 Retriever Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/retriever/agent.py` | `src/agents/retriever/agent.py` | ✅ 완료 | Retriever Agent |
| `server/agents/retriever/__init__.py` | `src/agents/retriever/__init__.py` | ✅ 완료 | 패키지 초기화 |

### 1.3 Extractor Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/extractor/__init__.py` | `src/agents/extractor/__init__.py` | ✅ 완료 | 패키지 초기화 |
| 구현 파일 | `src/agents/extractor/agent.py` | ✅ 완료 | Azure GPT-4o 연동 |

### 1.4 Wiki Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/wiki/__init__.py` | `src/agents/wiki/__init__.py` | ✅ 완료 | 패키지 초기화 |
| 구현 파일 | `src/agents/wiki/agent.py` | ✅ 완료 | Jinja2 템플릿 엔진 |

### 1.5 GraphViz Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/graphviz/__init__.py` | `src/agents/graphviz/__init__.py` | ✅ 완료 | 패키지 초기화 |
| 구현 파일 | `src/agents/graphviz/agent.py` | ✅ 완료 | streamlit-agraph 연동 |

### 1.6 Supervisor Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/supervisor/__init__.py` | `src/agents/supervisor/__init__.py` | ✅ 완료 | 패키지 초기화 |
| 구현 파일 | `src/agents/supervisor/agent.py` | ✅ 완료 | LangGraph 워크플로우 |

### 1.7 Feedback Agent
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/agents/feedback/__init__.py` | `src/agents/feedback/__init__.py` | ✅ 완료 | 패키지 초기화 |
| 구현 파일 | `src/agents/feedback/agent.py` | ✅ 완료 | SQLite + Slack Webhook |

## 2. 핵심 기능 파일 마이그레이션

### 2.1 스키마 (Schemas)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/schemas/base.py` | `src/core/schemas/base.py` | ✅ 완료 | 기본 메시지 스키마 |
| `server/schemas/agents.py` | `src/core/schemas/agents.py` | ✅ 완료 | 에이전트 입출력 스키마 |
| `server/schemas/__init__.py` | `src/core/schemas/__init__.py` | ✅ 완료 | 패키지 초기화 |

### 2.2 저장소 (Storage)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/retrieval/vector_store.py` | `src/core/storage/vector_store/vector_store.py` | ✅ 완료 | FAISS 벡터 스토어 |
| `server/retrieval/search_service.py` | `src/core/storage/vector_store/search_service.py` | ✅ 완료 | 검색 서비스 |
| `server/retrieval/__init__.py` | `src/core/storage/vector_store/__init__.py` | ✅ 완료 | 패키지 초기화 |
| `server/utils/kg_manager.py` | `src/core/utils/kg_manager.py` | ✅ 완료 | 지식 그래프 관리자 |
| `server/utils/storage_manager.py` | `src/core/utils/storage_manager.py` | ✅ 완료 | 저장소 관리자 |

### 2.3 워크플로우 (Workflow)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/workflow/graph.py` | `src/core/workflow/graph.py` | ✅ 완료 | LangGraph 워크플로우 |
| `server/workflow/state.py` | `src/core/workflow/state.py` | ✅ 완료 | 워크플로우 상태 |
| `server/workflow/agents/agent.py` | `src/core/workflow/agents/agent.py` | ✅ 완료 | 워크플로우 에이전트 |
| `server/workflow/agents/con_agent.py` | `src/core/workflow/agents/con_agent.py` | ✅ 완료 | 반대 에이전트 |
| `server/workflow/agents/judge_agent.py` | `src/core/workflow/agents/judge_agent.py` | ✅ 완료 | 판단 에이전트 |
| `server/workflow/agents/pro_agent.py` | `src/core/workflow/agents/pro_agent.py` | ✅ 완료 | 찬성 에이전트 |
| `server/workflow/agents/round_manager.py` | `src/core/workflow/agents/round_manager.py` | ✅ 완료 | 라운드 관리자 |

### 2.4 유틸리티 (Utils)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/utils/cache_manager.py` | `src/core/utils/cache_manager.py` | ⏳ 대기 | 캐시 관리자 |
| `server/utils/config.py` | `src/core/utils/config.py` | ⏳ 대기 | 설정 관리 |
| `server/utils/lock_manager.py` | `src/core/utils/lock_manager.py` | ⏳ 대기 | 락 관리자 |
| `server/utils/redis_manager.py` | `src/core/utils/redis_manager.py` | ⏳ 대기 | Redis 관리자 |
| `server/utils/scheduler.py` | `src/core/utils/scheduler.py` | ⏳ 대기 | 스케줄러 |

## 3. API 파일 마이그레이션

### 3.1 메인 애플리케이션
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/main.py` | `src/api/main.py` | ✅ 완료 | FastAPI 메인 앱 |
| `server/__init__.py` | `src/api/__init__.py` | ✅ 완료 | 패키지 초기화 |

### 3.2 라우터 (Routers)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/routers/checkpoints.py` | `src/api/routes/checkpoints.py` | ✅ 완료 | 체크포인트 API |
| `server/routers/history.py` | `src/api/routes/history.py` | ✅ 완료 | 히스토리 API |
| `server/routers/retriever.py` | `src/api/routes/retriever.py` | ✅ 완료 | Retriever API |
| `server/routers/workflow.py` | `src/api/routes/workflow.py` | ✅ 완료 | 워크플로우 API |
| `server/routers/__init__.py` | `src/api/routes/__init__.py` | ✅ 완료 | 패키지 초기화 |

## 4. UI 파일 마이그레이션

### 4.1 메인 애플리케이션
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `app/main.py` | `app/main.py` | ✅ 유지 | Streamlit 메인 앱 (경로 유지) |

### 4.2 컴포넌트 (Components)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `app/components/history.py` | `app/components/history.py` | ✅ 유지 | 히스토리 컴포넌트 |
| `app/components/sidebar.py` | `app/components/sidebar.py` | ✅ 유지 | 사이드바 컴포넌트 |
| `app/components/__init__.py` | `app/components/__init__.py` | ✅ 유지 | 패키지 초기화 |

### 4.3 유틸리티 (Utils)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `app/utils/state_manager.py` | `app/utils/state_manager.py` | ✅ 유지 | 상태 관리자 |

## 5. 설정 파일 마이그레이션

### 5.1 환경 설정
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `config/environment.template` | `config/environment.template` | ✅ 완료 | 환경 설정 템플릿 |
| `config/README.md` | `config/README.md` | ✅ 완료 | 설정 문서 |
| `config/__init__.py` | `config/__init__.py` | ✅ 완료 | 패키지 초기화 |

### 5.2 템플릿
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `prompts/README.md` | `config/templates/prompts/README.md` | ⏳ 대기 | 프롬프트 문서 |

## 6. 테스트 파일 마이그레이션

### 6.1 단위 테스트 (Unit Tests)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `tests/unit/test_cache_manager.py` | `tests/unit/core/test_cache_manager.py` | ⏳ 대기 | 캐시 관리자 테스트 |
| `tests/unit/test_example.py` | `tests/unit/core/test_example.py` | ⏳ 대기 | 예제 테스트 |
| `tests/unit/test_lock_manager.py` | `tests/unit/core/test_lock_manager.py` | ⏳ 대기 | 락 관리자 테스트 |
| `tests/unit/test_storage_manager.py` | `tests/unit/core/test_storage_manager.py` | ⏳ 대기 | 저장소 관리자 테스트 |
| `tests/unit/test_vector_store_benchmark.py` | `tests/unit/core/test_vector_store_benchmark.py` | ⏳ 대기 | 벡터 스토어 벤치마크 |
| `tests/agents/test_research_agent.py` | `tests/unit/agents/test_research_agent.py` | ⏳ 대기 | Research Agent 테스트 |
| `tests/agents/test_research_agent_performance.py` | `tests/performance/agents/test_research_agent_performance.py` | ⏳ 대기 | Research Agent 성능 테스트 |
| `tests/schemas/test_research_schemas.py` | `tests/unit/core/test_research_schemas.py` | ⏳ 대기 | Research 스키마 테스트 |

### 6.2 통합 테스트 (Integration Tests)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `tests/integration/test_api.py` | `tests/integration/api/test_api.py` | ⏳ 대기 | API 통합 테스트 |
| `tests/integration/test_redis_migration.py` | `tests/integration/workflow/test_redis_migration.py` | ⏳ 대기 | Redis 마이그레이션 테스트 |

### 6.3 엔드투엔드 테스트 (E2E Tests)
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `tests/e2e/test_knowledge_graph_workflow.py` | `tests/e2e/scenarios/test_knowledge_graph_workflow.py` | ⏳ 대기 | 지식 그래프 워크플로우 |
| `tests/e2e/test_system_integration.py` | `tests/e2e/scenarios/test_system_integration.py` | ⏳ 대기 | 시스템 통합 테스트 |

### 6.4 기타 테스트
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `tests/test_rdflib_integration.py` | `tests/unit/core/test_rdflib_integration.py` | ⏳ 대기 | RDFLib 통합 테스트 |
| `tests/benchmark_redis_migration.py` | `tests/performance/workflow/benchmark_redis_migration.py` | ⏳ 대기 | Redis 마이그레이션 벤치마크 |

## 7. 문서 파일 마이그레이션

### 7.1 아키텍처 문서
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `docs/architecture/directory_structure_design.md` | `docs/architecture/directory_structure_design.md` | ✅ 완료 | 디렉토리 구조 설계 |
| `docs/architecture/migration_mapping.md` | `docs/architecture/migration_mapping.md` | ✅ 완료 | 마이그레이션 매핑 |
| `docs/performance_optimization_report.md` | `docs/performance_optimization_report.md` | ✅ 완료 | 성능 최적화 보고서 |

### 7.2 기타 문서
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `PROJECT_STRUCTURE.md` | `docs/architecture/PROJECT_STRUCTURE.md` | ⏳ 대기 | 프로젝트 구조 문서 |
| `REDIS_MIGRATION_REPORT.md` | `docs/deployment/REDIS_MIGRATION_REPORT.md` | ⏳ 대기 | Redis 마이그레이션 보고서 |
| `SYSTEM_INTEGRATION_REPORT.md` | `docs/deployment/SYSTEM_INTEGRATION_REPORT.md` | ⏳ 대기 | 시스템 통합 보고서 |
| `WEB_SEARCH_MIGRATION_SUMMARY.md` | `docs/deployment/WEB_SEARCH_MIGRATION_SUMMARY.md` | ⏳ 대기 | 웹 검색 마이그레이션 요약 |

## 8. 설정 파일 마이그레이션

### 8.1 프로젝트 설정
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `requirements.txt` | `requirements.txt` | ✅ 유지 | 프로젝트 루트 유지 |
| `requirements-dev.txt` | `requirements-dev.txt` | ✅ 유지 | 개발 의존성 |
| `requirements-prod.txt` | `requirements-prod.txt` | ✅ 유지 | 운영 의존성 |
| `pytest.ini` | `pytest.ini` | ✅ 유지 | pytest 설정 |
| `docker-compose.yml` | `docker-compose.yml` | ✅ 유지 | Docker Compose |
| `Makefile` | `Makefile` | ✅ 유지 | 빌드 스크립트 |

### 8.2 Docker 파일
| 현재 위치 | 새 위치 | 상태 | 비고 |
|-----------|---------|------|------|
| `server/Dockerfile` | `src/api/Dockerfile` | ⏳ 대기 | API 서버 Dockerfile |
| `app/Dockerfile` | `src/ui/Dockerfile` | ⏳ 대기 | UI 서버 Dockerfile |

## 9. 삭제 예정 파일

### 9.1 백업 파일
| 현재 위치 | 삭제 이유 | 상태 |
|-----------|-----------|------|
| `server/agents/research/research_agent.py.backup` | 모듈화 완료 | ⏳ 대기 |

### 9.2 중복 파일
| 현재 위치 | 삭제 이유 | 상태 |
|-----------|-----------|------|
| `dirTree.txt` | 자동 생성 파일 | ⏳ 대기 |
| `test_app.py` | 테스트 구조 개선 | ⏳ 대기 |

## 10. 마이그레이션 우선순위

### Phase 1: 핵심 기능 (높은 우선순위)
1. **스키마 마이그레이션**: `server/schemas/` → `src/core/schemas/`
2. **저장소 마이그레이션**: `server/retrieval/` → `src/core/storage/`
3. **유틸리티 마이그레이션**: `server/utils/` → `src/core/utils/`

### Phase 2: 에이전트 (중간 우선순위)
1. **Retriever Agent**: `server/agents/retriever/` → `src/agents/retriever/`
2. **Extractor Agent**: 구현 및 마이그레이션
3. **Wiki Agent**: 구현 및 마이그레이션
4. **GraphViz Agent**: 구현 및 마이그레이션
5. **Supervisor Agent**: 구현 및 마이그레이션
6. **Feedback Agent**: 구현 및 마이그레이션

### Phase 3: API 및 UI (낮은 우선순위)
1. **API 마이그레이션**: `server/` → `src/api/`
2. **UI 마이그레이션**: `app/` → `src/ui/`

### Phase 4: 테스트 및 문서 (마지막)
1. **테스트 구조 개선**: 기존 테스트 파일 재배치
2. **문서 정리**: 문서 파일 재배치

## 11. 주의사항

### 11.1 Import 경로 변경
- 모든 import 문을 새로운 경로로 업데이트 필요
- 상대 import를 절대 import로 변경 권장
- 순환 의존성 방지

### 11.2 의존성 관리
- 각 모듈의 의존성을 명확히 정의
- 공통 의존성은 `src/core/`에 배치
- 에이전트별 의존성은 각 에이전트 디렉토리에 배치

### 11.3 테스트 구조
- 단위 테스트: 각 모듈별 독립적 테스트
- 통합 테스트: 모듈 간 상호작용 테스트
- 성능 테스트: 성능 및 부하 테스트
- E2E 테스트: 전체 시스템 시나리오 테스트

### 11.4 문서화
- 각 모듈의 목적과 기능을 명시
- API 문서 자동 생성 고려
- 마이그레이션 가이드 유지보수

## 12. 검증 체크리스트

### 12.1 기능 검증
- [ ] 모든 import 경로 정상 동작
- [ ] 테스트 실행 성공
- [ ] API 엔드포인트 정상 동작
- [ ] UI 컴포넌트 정상 동작

### 12.2 성능 검증
- [ ] 마이그레이션 후 성능 저하 없음
- [ ] 메모리 사용량 정상
- [ ] 응답 시간 유지

### 12.3 문서 검증
- [ ] README 파일 업데이트
- [ ] API 문서 업데이트
- [ ] 마이그레이션 가이드 완성

---

**마지막 업데이트**: 2025-01-27
**버전**: 1.0.0
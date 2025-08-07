# AI Knowledge Graph System - 문서

이 디렉토리는 AI Knowledge Graph System의 모든 문서를 포함합니다.

## 📚 문서 구조

```
docs/
├── README.md                    # 이 파일 - 문서 개요
├── architecture/                # 아키텍처 문서
│   ├── project_structure.md     # 프로젝트 구조 설명
│   ├── migration_summary.md     # 마이그레이션 요약
│   ├── import_path_mapping.md   # Import 경로 매핑
│   ├── file_migration_mapping.md # 파일별 마이그레이션 상태
│   ├── directory_structure_design.md # 디렉토리 구조 설계
│   ├── migration_mapping.md     # 마이그레이션 매핑
│   ├── MIGRATION_REPORT.md      # Core 패키지 마이그레이션 보고서
│   ├── REDIS_MIGRATION_REPORT.md # Redis → Pure Python 마이그레이션 보고서
│   └── WEB_SEARCH_MIGRATION_SUMMARY.md # SerpAPI → DuckDuckGo 마이그레이션 보고서
├── api/                         # API 문서
│   └── rest_api_guide.md        # REST API 사용 가이드
├── user_guide/                  # 사용자 가이드
│   └── getting_started.md       # 시작 가이드
├── deployment/                  # 배포 문서
│   └── deployment_guide.md      # 배포 가이드
├── performance_optimization_report.md # 성능 최적화 보고서
└── SYSTEM_INTEGRATION_REPORT.md # 시스템 통합 검증 보고서
```

## 🎯 문서별 개요

### 아키텍처 문서 (`architecture/`)

#### [프로젝트 구조](./architecture/project_structure.md)
- 새로운 `src/` 기반 디렉토리 구조 설명
- 모듈별 역할 및 책임
- Import 경로 규칙
- 마이그레이션 상태

#### [마이그레이션 요약](./architecture/migration_summary.md)
- 기존 구조에서 새로운 구조로의 마이그레이션 계획
- 단계별 실행 계획
- 위험 요소 및 대응 방안
- 검증 체크리스트

#### [Import 경로 매핑](./architecture/import_path_mapping.md)
- 기존 Import 경로 → 새로운 Import 경로 매핑
- 모듈별 Import 규칙
- 호환성 유지 방안

#### [파일 마이그레이션 매핑](./architecture/file_migration_mapping.md)
- 파일별 마이그레이션 상태 추적
- 백업 및 복원 전략
- 의존성 관리

#### [Core 패키지 마이그레이션 보고서](./architecture/MIGRATION_REPORT.md)
- Core 패키지 마이그레이션 상세 보고서
- 마이그레이션 과정 및 결과
- 문제점 및 해결 방안

#### [Redis 마이그레이션 보고서](./architecture/REDIS_MIGRATION_REPORT.md)
- Redis → Pure Python 마이그레이션 상세 보고서
- 성능 비교 및 벤치마크 결과
- 마이그레이션 전략 및 실행 과정

#### [웹 검색 마이그레이션 요약](./architecture/WEB_SEARCH_MIGRATION_SUMMARY.md)
- SerpAPI → DuckDuckGo 마이그레이션 요약
- 변경 사유 및 영향도 분석
- 마이그레이션 결과

### API 문서 (`api/`)

#### [REST API 가이드](./api/rest_api_guide.md)
- 모든 API 엔드포인트 설명
- 요청/응답 예제
- 에러 처리 방법
- 성능 고려사항
- 테스트 예제

### 사용자 가이드 (`user_guide/`)

#### [시작 가이드](./user_guide/getting_started.md)
- 시스템 요구사항
- 환경 설정 방법
- 기본 사용법
- 문제 해결 가이드
- 고급 기능 사용법

### 배포 문서 (`deployment/`)

#### [배포 가이드](./deployment/deployment_guide.md)
- Docker 배포 방법
- 클라우드 배포 (AWS, GCP, Azure)
- 환경별 설정
- 모니터링 및 로깅
- 보안 설정
- 성능 최적화

### 기술 보고서

#### [성능 최적화 보고서](./performance_optimization_report.md)
- Research Agent 성능 테스트 결과
- 최적화 적용사항
- 성능 개선 효과
- 권장사항

#### [시스템 통합 검증 보고서](./SYSTEM_INTEGRATION_REPORT.md)
- 전체 시스템 통합 검증 결과
- 컴포넌트 간 상호작용 테스트
- 성능 및 안정성 검증
- 문제점 및 개선사항

## 📖 추가 기술 문서

프로젝트 루트에 있는 추가 기술 문서들:

- **[README.md](../README.md)**: 프로젝트 메인 문서

## 🔍 문서 검색

### 빠른 참조

| 주제 | 문서 | 설명 |
|------|------|------|
| **시작하기** | [시작 가이드](./user_guide/getting_started.md) | 처음 사용자를 위한 가이드 |
| **API 사용** | [REST API 가이드](./api/rest_api_guide.md) | API 엔드포인트 및 사용법 |
| **배포** | [배포 가이드](./deployment/deployment_guide.md) | 다양한 환경에서의 배포 방법 |
| **아키텍처** | [프로젝트 구조](./architecture/project_structure.md) | 시스템 아키텍처 및 구조 |
| **성능** | [성능 최적화 보고서](./performance_optimization_report.md) | 성능 테스트 및 최적화 결과 |
| **시스템 통합** | [시스템 통합 보고서](./SYSTEM_INTEGRATION_REPORT.md) | 전체 시스템 통합 검증 결과 |

### 개발자 가이드

#### 새로운 기능 개발
1. [프로젝트 구조](./architecture/project_structure.md) 확인
2. [Import 경로 매핑](./architecture/import_path_mapping.md) 참조
3. [REST API 가이드](./api/rest_api_guide.md)에서 API 설계 패턴 확인

#### 마이그레이션 작업
1. [마이그레이션 요약](./architecture/migration_summary.md) 확인
2. [파일 마이그레이션 매핑](./architecture/file_migration_mapping.md) 참조
3. [Import 경로 매핑](./architecture/import_path_mapping.md) 적용
4. [Core 패키지 마이그레이션 보고서](./architecture/MIGRATION_REPORT.md) 참조
5. [Redis 마이그레이션 보고서](./architecture/REDIS_MIGRATION_REPORT.md) 참조

#### 배포 및 운영
1. [배포 가이드](./deployment/deployment_guide.md) 참조
2. [성능 최적화 보고서](./performance_optimization_report.md) 확인
3. [시작 가이드](./user_guide/getting_started.md)의 문제 해결 섹션 참조
4. [시스템 통합 보고서](./SYSTEM_INTEGRATION_REPORT.md) 확인

## 📝 문서 작성 가이드라인

### 문서 작성 원칙
1. **명확성**: 복잡한 개념도 이해하기 쉽게 설명
2. **완성성**: 필요한 모든 정보 포함
3. **일관성**: 용어와 형식 통일
4. **실용성**: 실제 사용 사례와 예제 포함

### 문서 형식
- **Markdown** 형식 사용
- **한국어**로 작성 (기술 용어는 영문 병기)
- **이모지**를 활용한 섹션 구분
- **코드 블록**에 언어 명시
- **링크**를 활용한 문서 간 연결

### 문서 업데이트
- 기능 변경 시 관련 문서 동시 업데이트
- 버전 정보 및 날짜 표시
- 변경 이력 관리

## 🤝 문서 개선

### 기여 방법
1. **이슈 리포트**: 문서 오류나 개선점 발견 시 GitHub Issues에 등록
2. **Pull Request**: 문서 개선 제안 시 PR 생성
3. **토론**: GitHub Discussions에서 문서 관련 논의

### 개선 우선순위
1. **높음**: 사용자 가이드, API 문서, 시작 가이드
2. **중간**: 아키텍처 문서, 배포 가이드
3. **낮음**: 기술 보고서, 마이그레이션 문서

## 📞 지원

- **문서 관련 질문**: GitHub Discussions
- **기술 지원**: GitHub Issues
- **기능 요청**: GitHub Issues (Feature Request 라벨)

---

*마지막 업데이트: 2025-08-07*
*문서 버전: 1.1.0* 
# DECISIONS.md — Architecture Decision Records

> **Purpose**: Log significant technical decisions and their rationale.

## Decisions

## [DECISION-001] HXSK 개발 방법론 채택

**Date**: 2026-03-31
**Status**: Accepted

### Context
AI 에이전트 기반 개발에서 일관된 워크플로우와 메모리 시스템이 필요

### Decision
HExoskeleton(HXSK) 방법론을 프로젝트에 적용

### Rationale
순수 bash + 마크다운 기반으로 외부 종속성 없이 어떤 코딩 에이전트든 사용 가능

### Consequences
- SPEC→PLAN→EXECUTE→VERIFY 워크플로우 준수 필요
- .hxsk/ 디렉토리 구조 유지 필요

### Alternatives Considered
- 별도 방법론 없이 자유로운 개발 → 세션 간 컨텍스트 손실 우려

---

*Last updated: 2026-03-31*

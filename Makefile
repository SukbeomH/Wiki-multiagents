# AI Knowledge Graph System - Makefile

.PHONY: help install test test-unit test-integration test-e2e test-coverage clean lint format docker-build docker-up docker-down

# 기본 목표
help: ## 사용 가능한 명령어 표시
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# 설치 및 설정
install: ## 의존성 설치
	pip install -r requirements.txt

install-dev: ## 개발 의존성 설치
	pip install -r requirements.txt

# 테스트 실행
test: ## 모든 테스트 실행
	pytest

test-unit: ## 단위 테스트만 실행
	pytest tests/unit -m unit

test-integration: ## 통합 테스트만 실행
	pytest tests/integration -m integration

test-e2e: ## E2E 테스트만 실행
	pytest tests/e2e -m e2e

test-agents: ## 에이전트 테스트만 실행
	pytest tests/agents -m agent

test-coverage: ## 커버리지 리포트 생성
	pytest --cov=server --cov=app --cov-report=html --cov-report=term

test-fast: ## 빠른 테스트 (slow 제외)
	pytest -m "not slow"

test-slow: ## 느린 테스트만 실행
	pytest -m slow

# 코드 품질
lint: ## 코드 린팅
	flake8 src/ app/ tests/
	mypy server/ app/

format: ## 코드 포맷팅
	black src/ app/ tests/
	isort src/ app/ tests/

format-check: ## 포맷팅 확인 (CI용)
	black --check src/ app/ tests/
	isort --check-only src/ app/ tests/

# 시스템 실행
start: ## 통합 스크립트로 시스템 시작 (권장)
	python start_system.py

start-ui: ## UI만 실행 (개발용)
	streamlit run src/ui/main.py --server.port 8501

start-api: ## API 서버만 실행 (개발용)
	uvicorn src.api.main:app --reload --port 8000 --host localhost

# Docker 관련
docker-build: ## Docker 이미지 빌드
	docker-compose build

docker-up: ## Docker 서비스 시작
	docker-compose up -d

docker-up-dev: ## 개발용 Docker 서비스 시작 (dev 프로필 포함)
	docker-compose --profile dev up -d

docker-down: ## Docker 서비스 중지
	docker-compose down

docker-logs: ## Docker 로그 확인
	docker-compose logs -f

# 환경 설정
setup-env: ## 환경변수 파일 생성
	@if [ ! -f .env ]; then \
		cp config/environment.template .env; \
		echo "✅ .env 파일이 생성되었습니다. 필요한 값들을 설정해주세요."; \
	else \
		echo "⚠️  .env 파일이 이미 존재합니다."; \
	fi

# 정리
clean: ## 임시 파일 정리
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/

clean-docker: ## Docker 관련 정리
	docker-compose down -v
	docker system prune -f

# 데이터베이스
db-reset: ## 테스트 데이터베이스 초기화
	rm -f test.db

# 개발 환경
dev-setup: install-dev setup-env ## 개발 환경 전체 설정
	@echo "✅ 개발 환경 설정이 완료되었습니다."
	@echo "1. .env 파일의 값들을 설정해주세요"
	@echo "2. 'make docker-up-dev'로 서비스를 시작하세요"

# CI 관련
ci-test: format-check lint test-coverage ## CI에서 실행할 테스트 (포맷팅, 린팅, 커버리지)

# 헬프가 기본값
.DEFAULT_GOAL := help
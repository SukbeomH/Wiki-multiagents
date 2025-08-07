"""
pytest 설정 및 공통 픽스처

이 파일은 모든 테스트에서 사용할 수 있는 공통 픽스처와 설정을 제공합니다.
"""

import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Redis 마이그레이션 완료로 제거됨
# from redis import Redis

# 테스트 환경 설정
os.environ["TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite:///./test.db"
# Redis 대체 완료 - diskcache 기반 테스트 환경
os.environ["TEST_CACHE_DIR"] = "./test_data/cache"
os.environ["TEST_LOCK_DIR"] = "./test_data/locks"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """세션 범위의 이벤트 루프 생성"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """테스트용 환경변수 설정"""
    test_env = {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test_key",
        "AZURE_OPENAI_DEPLOY_GPT4O": "test_gpt4o",
            "TEST_RDFLIB_STORE_URI": "sqlite:///./test_kg.db",
        "CACHE_DIR": "./test_data/cache",
        "LOCK_DIR": "./test_data/locks",
        "JWT_SECRET_KEY": "test_secret_key_for_testing_only",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def test_db_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False}
    )
    return engine


@pytest.fixture
def test_db_session(test_db_engine):
    """테스트용 데이터베이스 세션"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_storage_manager():
    """Mock StorageManager (Redis 대체)"""
    from server.utils.storage_manager import StorageManager
    mock = Mock(spec=StorageManager)
    mock.test_connection.return_value = True
    mock.get_sync_client.return_value = None  # fakeredis 없을 수 있음
    mock.is_locked.return_value = False
    return mock


# Neo4j 관련 코드는 RDFLib 마이그레이션으로 제거됨


@pytest.fixture
def mock_openai_client():
    """Mock Azure OpenAI 클라이언트"""
    mock = AsyncMock()
    mock.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="Test response",
                    role="assistant"
                )
            )
        ]
    )
    return mock


@pytest.fixture
def api_client(mock_env_vars):
    """FastAPI 테스트 클라이언트"""
    from server.main import app
    return TestClient(app)


@pytest.fixture
def sample_document():
    """테스트용 샘플 문서"""
    return {
        "id": "doc_001",
        "title": "AI Knowledge Graphs",
        "content": "Knowledge graphs are powerful tools for organizing information...",
        "url": "https://example.com/article",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_entities():
    """테스트용 샘플 엔티티"""
    return [
        {
            "id": "entity_1",
            "type": "TECHNOLOGY",
            "name": "Knowledge Graph",
            "extra": {"description": "A graph-based data model"}
        },
        {
            "id": "entity_2", 
            "type": "CONCEPT",
            "name": "Artificial Intelligence",
            "extra": {"description": "Machine intelligence"}
        }
    ]


@pytest.fixture
def sample_relations():
    """테스트용 샘플 관계"""
    return [
        {
            "source": "entity_1",
            "target": "entity_2",
            "predicate": "RELATED_TO",
            "confidence": 0.85
        }
    ]


@pytest.fixture
def sample_vector():
    """테스트용 샘플 벡터"""
    import numpy as np
    return np.random.rand(384).astype('float32')  # sentence-transformers 기본 차원


# 테스트 마커별 설정
def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "unit: Unit test marker"
    )
    config.addinivalue_line(
        "markers", "integration: Integration test marker"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end test marker"
    )
    config.addinivalue_line(
        "markers", "slow: Slow test marker"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 컬렉션 수정"""
    # slow 마커가 있는 테스트는 기본적으로 skip
    skip_slow = pytest.mark.skip(reason="slow test skipped by default")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
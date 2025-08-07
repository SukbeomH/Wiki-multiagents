import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
# LangChain OpenAI 임포트 (선택적)
try:
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    AzureChatOpenAI = None
    AzureOpenAIEmbeddings = None
# Redis 대체 완료 - StorageManager에서 RedisConfig import

# .env 파일에서 환경 변수 로드
load_dotenv()


class Settings(BaseSettings):
    # Azure OpenAI 설정
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOY_GPT4O: str
    AZURE_OPENAI_DEPLOY_EMBED_3_LARGE: str
    AZURE_OPENAI_API_VERSION: str

    # Langfuse 설정 (선택적)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = ""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Debate Arena API"

    # CORS 설정
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # SQLite 데이터베이스 설정
    DB_PATH: str = "history.db"
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///./{DB_PATH}"
    
    # Cache & Storage 설정 (Redis 대체 완료)
    # 캐시 및 락 설정은 환경변수에서 직접 로드
    
    # RDFLib Knowledge Graph 설정 (Neo4j 대체)
    RDFLIB_STORE_URI: str = "sqlite:///./data/kg.db"
    RDFLIB_GRAPH_IDENTIFIER: str = "kg"
    RDFLIB_NAMESPACE_PREFIX: str = "http://example.org/kg/"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra='ignore')

    def get_llm(self):
        """Azure OpenAI LLM 인스턴스를 반환합니다."""
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("langchain_openai가 사용 불가능합니다")
        
        return AzureChatOpenAI(
            openai_api_key=self.AZURE_OPENAI_API_KEY,
            azure_endpoint=self.AZURE_OPENAI_ENDPOINT,
            azure_deployment=self.AZURE_OPENAI_DEPLOY_GPT4O,
            api_version=self.AZURE_OPENAI_API_VERSION,
            temperature=0.7,
            streaming=True,  # 스트리밍 활성화
        )

    def get_embeddings(self):
        """Azure OpenAI Embeddings 인스턴스를 반환합니다."""
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("langchain_openai가 사용 불가능합니다")
        
        return AzureOpenAIEmbeddings(
            model=self.AZURE_OPENAI_DEPLOY_EMBED_3_LARGE,
            openai_api_version=self.AZURE_OPENAI_API_VERSION,
            api_key=self.AZURE_OPENAI_API_KEY,
            azure_endpoint=self.AZURE_OPENAI_ENDPOINT,
        )
    
    def get_cache_config(self):
        """캐시 설정을 반환합니다 (Redis 대체)"""
        from .cache_manager import CacheConfig
        return CacheConfig.from_env()


# 설정 인스턴스 생성
settings = Settings()


# 편의를 위한 함수들, 하위 호환성을 위해 유지
def get_llm():
    return settings.get_llm()


def get_embeddings():
    return settings.get_embeddings()

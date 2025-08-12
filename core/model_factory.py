"""
Azure OpenAI 모델 팩토리 모듈
"""
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from core.config import Config
from core.logger import logger


class AzureModelFactory:
    """Azure OpenAI 모델 인스턴스를 중앙에서 관리하고 생성하는 헬퍼 클래스."""
    
    def __init__(self):
        self.endpoint = os.getenv("AOAI_ENDPOINT")
        self.api_key = os.getenv("AOAI_API_KEY")
        self.gpt4o_deployment = os.getenv("AOAI_DEPLOY_GPT4O")
        self.embedding_deployment = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")
        self._chat_model_cache = {}
        self._embedding_model_cache = None

    def get_chat_model(self, temperature: float = 0) -> AzureChatOpenAI:
        """채팅 모델 인스턴스를 반환합니다. 캐싱을 통해 성능을 최적화합니다."""
        cache_key = f"chat_{temperature}"
        if cache_key not in self._chat_model_cache:
            logger.info("[model] AzureChatOpenAI 인스턴스 생성 (temp=%s)", temperature)
            self._chat_model_cache[cache_key] = AzureChatOpenAI(
                azure_deployment=self.gpt4o_deployment,
                api_version=Config.AZURE_API_VERSION,
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                temperature=temperature,
                max_retries=5,
                timeout=60,
                request_timeout=60,
            )
        return self._chat_model_cache[cache_key]

    def get_embedding_model(self) -> AzureOpenAIEmbeddings:
        """임베딩 모델 인스턴스를 반환합니다. 싱글톤 패턴으로 캐싱합니다."""
        if self._embedding_model_cache is None:
            logger.info("[model] AzureOpenAIEmbeddings 인스턴스 생성")
            self._embedding_model_cache = AzureOpenAIEmbeddings(
                azure_deployment=self.embedding_deployment,
                api_version=Config.AZURE_API_VERSION,
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
            )
        return self._embedding_model_cache

    def clear_cache(self):
        """모델 캐시를 초기화합니다."""
        self._chat_model_cache.clear()
        self._embedding_model_cache = None
        logger.info("[model] 모델 캐시 초기화 완료") 
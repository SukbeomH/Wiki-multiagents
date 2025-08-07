#!/usr/bin/env python3
"""
Retriever Agent 구현
쿼리 텍스트를 임베딩으로 변환하고 FAISS Vector Store에서 유사도 검색을 수행
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.core.schemas.agents import RetrieverIn, RetrieverOut
from src.core.utils.config import settings
from src.core.storage.vector_store.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """
    Retriever Agent 클래스
    
    기능:
    1. 쿼리 텍스트를 Azure OpenAI 임베딩으로 변환
    2. FAISS Vector Store에서 유사도 검색 수행
    3. 검색 결과를 RetrieverOut 형태로 반환
    """
    
    def __init__(self):
        """
        Retriever Agent 초기화
        
        FAISSVectorStore는 기본 설정으로 초기화되며,
        인덱스 파일은 data/vector_indices/ 디렉토리에 자동 저장됩니다.
        """
        self.vector_store = FAISSVectorStore(
            dimension=4096,  # text-embedding-3-large 차원
            nlist=256,       # IVF 클러스터 수
            nprobe=16,       # 검색 시 탐색할 클러스터 수
            hnsw_m=32,       # HNSW 연결 수
            metric="L2"      # L2 거리 메트릭
        )
        self._embeddings_client = None
        
    @property
    def embeddings_client(self):
        """Azure OpenAI 임베딩 클라이언트 지연 로딩"""
        if self._embeddings_client is None:
            try:
                self._embeddings_client = settings.get_embeddings()
                logger.info("Azure OpenAI 임베딩 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"임베딩 클라이언트 초기화 실패: {e}")
                raise
        return self._embeddings_client
    
    def create_query_embedding(self, query: str) -> np.ndarray:
        """
        쿼리 텍스트를 4096차원 임베딩 벡터로 변환
        
        Args:
            query: 검색 쿼리 텍스트
            
        Returns:
            numpy.ndarray: 4096차원 임베딩 벡터
            
        Raises:
            ValueError: 임베딩 생성 실패 시
        """
        try:
            # Azure OpenAI를 통한 임베딩 생성
            embedding_vector = self.embeddings_client.embed_query(query)
            
            # numpy 배열로 변환
            vector = np.array(embedding_vector, dtype=np.float32)
            
            # 차원 검증
            if vector.shape[0] != 4096:
                raise ValueError(f"임베딩 차원이 올바르지 않습니다: {vector.shape[0]} != 4096")
            
            logger.debug(f"쿼리 임베딩 생성 완료: {query[:50]}... -> {vector.shape}")
            return vector
            
        except Exception as e:
            logger.error(f"쿼리 임베딩 생성 실패: {e}")
            raise ValueError(f"임베딩 생성 실패: {str(e)}")
    
    def process(self, input_data: RetrieverIn) -> RetrieverOut:
        """
        Retriever Agent 메인 처리 함수
        
        Args:
            input_data: RetrieverIn 입력 데이터
            
        Returns:
            RetrieverOut: 검색 결과
            
        Raises:
            ValueError: 처리 실패 시
        """
        try:
            logger.info(f"Retriever 검색 시작: '{input_data.query}' (top_k={input_data.top_k})")
            
            # 1. 쿼리 임베딩 생성
            query_vector = self.create_query_embedding(input_data.query)
            
            # 2. FAISS 유사도 검색
            search_results = self.vector_store.search(
                query_vector=query_vector,
                top_k=input_data.top_k,
                score_threshold=input_data.similarity_threshold,
                include_metadata=input_data.include_metadata
            )
            
            # 3. 결과 처리
            doc_ids = [str(doc_id) for doc_id in search_results["ids"]]
            similarities = search_results["distances"].tolist()
            metadata = search_results.get("metadata", [])
            
            # 4. 컨텍스트 텍스트 생성 (메타데이터에서 텍스트 추출)
            context_parts = []
            for i, meta in enumerate(metadata):
                if isinstance(meta, dict) and "text" in meta:
                    context_parts.append(f"[문서 {doc_ids[i]}] {meta['text']}")
                elif isinstance(meta, dict) and "content" in meta:
                    context_parts.append(f"[문서 {doc_ids[i]}] {meta['content']}")
                else:
                    context_parts.append(f"[문서 {doc_ids[i]}] (내용 없음)")
            
            context = "\n\n".join(context_parts) if context_parts else ""
            
            # 5. 결과 반환
            result = RetrieverOut(
                doc_ids=doc_ids,
                context=context,
                similarities=similarities,
                metadata=metadata
            )
            
            logger.info(f"Retriever 검색 완료: {len(doc_ids)}개 문서 반환")
            return result
            
        except Exception as e:
            logger.error(f"Retriever 처리 실패: {e}")
            raise ValueError(f"검색 처리 실패: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Retriever Agent 상태 점검
        
        Returns:
            Dict: 상태 정보
        """
        try:
            # 임베딩 클라이언트 확인
            embeddings_healthy = False
            try:
                test_vector = self.create_query_embedding("health check")
                embeddings_healthy = len(test_vector) == 4096
            except Exception as e:
                logger.warning(f"임베딩 클라이언트 상태 점검 실패: {e}")
            
            # Vector Store 상태 확인
            vector_store_stats = self.vector_store.get_index_stats()
            
            return {
                "status": "healthy" if embeddings_healthy and vector_store_stats["index_trained"] else "degraded",
                "embeddings_client": "healthy" if embeddings_healthy else "error",
                "vector_store": vector_store_stats,
                "capabilities": {
                    "embedding_dimension": 4096,
                    "model": "text-embedding-3-large",
                    "max_top_k": 20
                }
            }
            
        except Exception as e:
            logger.error(f"상태 점검 실패: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# 전역 인스턴스 생성 (싱글톤 패턴)
_retriever_agent = None

def get_retriever_agent() -> RetrieverAgent:
    """
    Retriever Agent 싱글톤 인스턴스 반환
    
    Returns:
        RetrieverAgent: 싱글톤 인스턴스
    """
    global _retriever_agent
    if _retriever_agent is None:
        _retriever_agent = RetrieverAgent()
        logger.info("Retriever Agent 싱글톤 인스턴스 생성")
    return _retriever_agent
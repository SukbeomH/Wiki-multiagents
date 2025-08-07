"""
AI Knowledge Graph System - FAISS Vector Store

FAISS IVF-HNSW 인덱스를 사용한 고성능 벡터 검색 시스템
PRD 요구사항에 따른 4096차원 벡터 지원
"""

import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import pickle
import json
from datetime import datetime, UTC

# FAISS 조건부 import
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError as e:
    FAISS_AVAILABLE = False
    faiss = None
    logging.warning(f"FAISS not available: {e}")

logger = logging.getLogger(__name__)


class FAISSVectorStoreConfig:
    """FAISS 벡터 스토어 설정 - PRD 요구사항"""
    
    # PRD 요구사항에 따른 정확한 설정값
    DIMENSION = 4096         # PRD 요구사항: 4096차원
    NLIST = 256             # PRD 요구사항: IVF 클러스터 수 
    NPROBE = 16             # PRD 요구사항: 검색 시 탐색할 클러스터 수
    HNSW_M = 32             # PRD 요구사항: HNSW 연결 수
    METRIC = "L2"           # PRD 요구사항: L2 거리 메트릭
    
    # 성능 최적화 설정
    BATCH_SIZE = 1000       # 배치 삽입 크기
    TRAIN_SIZE = 10000      # 훈련에 필요한 최소 벡터 수
    
    # 저장 설정
    DATA_DIR = "data/vector_indices"
    INDEX_FILE = "faiss_index.bin"
    METADATA_FILE = "metadata.json"
    ID_MAP_FILE = "id_mapping.pkl"


class FAISSVectorStore:
    """
    FAISS IVF-HNSW 인덱스 기반 벡터 스토어
    
    PRD 요구사항 구현:
    - 4096차원 벡터 지원
    - IVF-HNSW 인덱스 (nlist=256, nprobe=16, M=32)
    - 고성능 유사도 검색
    - 디스크 저장 및 로드 지원
    """
    
    def __init__(self, dimension=4096, nlist=256, nprobe=16, hnsw_m=32, metric="L2"):
        """FAISS 벡터 스토어 초기화"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not available. Please install faiss-cpu or faiss-gpu.")
        
        self.dimension = dimension
        self.nlist = nlist
        self.nprobe = nprobe
        self.hnsw_m = hnsw_m
        self.metric = metric.upper()
        
        # 데이터 디렉토리 설정
        self.data_dir = Path(FAISSVectorStoreConfig.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 인덱스 및 메타데이터 초기화
        self.index = None
        self.id_to_external = {}
        self.external_to_id = {}
        self.metadata = {}
        self.next_id = 0
        
        # 인덱스 초기화
        self._create_index()
        
        logger.info(f"FAISSVectorStore initialized: dim={dimension}, nlist={nlist}, nprobe={nprobe}")
    
    def _create_index(self):
        """FAISS IVF-HNSW 인덱스 생성"""
        logger.info("Creating FAISS IVF-HNSW index")
        
        if self.metric == "L2":
            # L2 거리 메트릭
            quantizer = faiss.IndexHNSWFlat(self.dimension, self.hnsw_m)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist, faiss.METRIC_L2)
        elif self.metric == "IP":
            # 내적 메트릭 (코사인 유사도)
            quantizer = faiss.IndexHNSWFlat(self.dimension, self.hnsw_m, faiss.METRIC_INNER_PRODUCT)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist, faiss.METRIC_INNER_PRODUCT)
        else:
            raise ValueError(f"Unsupported metric: {self.metric}")
        
        # nprobe 설정
        self.index.nprobe = self.nprobe
        
        logger.info(f"FAISS index created successfully: {type(self.index).__name__}")
    
    def is_trained(self):
        """인덱스 훈련 상태 확인"""
        return self.index is not None and self.index.is_trained
    
    def train(self, training_vectors):
        """인덱스 훈련"""
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        if self.is_trained():
            logger.info("Index is already trained")
            return
        
        logger.info(f"Training FAISS index with {training_vectors.shape[0]} vectors")
        training_vectors = training_vectors.astype(np.float32)
        
        if training_vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {training_vectors.shape[1]}")
        
        self.index.train(training_vectors)
        logger.info("Index training completed successfully")
    
    def add_vectors(
        self, 
        vectors, 
        external_ids=None, 
        metadata=None, 
        batch_size=None, 
        auto_save=False,
        verify_insertion=True
    ):
        """
        벡터 배치 삽입 - PRD 요구사항 구현
        
        Args:
            vectors: 추가할 벡터 (np.ndarray, shape: [n_vectors, dimension])
            external_ids: 외부 ID 리스트 (선택적)
            metadata: 벡터별 메타데이터 (선택적)
            batch_size: 배치 처리 크기 (기본: FAISSVectorStoreConfig.BATCH_SIZE)
            auto_save: 삽입 후 자동 저장 여부 (기본: False)
            verify_insertion: 삽입 후 크기 검증 여부 (기본: True)
            
        Returns:
            List[int]: 할당된 내부 ID 리스트
        """
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        # 입력 검증
        if not isinstance(vectors, np.ndarray):
            vectors = np.array(vectors)
        
        vectors = vectors.astype(np.float32)
        
        if vectors.ndim != 2:
            raise ValueError(f"Vectors must be 2D array, got shape: {vectors.shape}")
        
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {vectors.shape[1]}")
        
        n_vectors = vectors.shape[0]
        if n_vectors == 0:
            logger.warning("No vectors to add")
            return []
        
        # 인덱스 훈련 확인
        if not self.is_trained():
            logger.info("Index not trained. Training with provided vectors...")
            self.train(vectors)
        
        # 배치 크기 설정
        if batch_size is None:
            batch_size = FAISSVectorStoreConfig.BATCH_SIZE
        
        # 외부 ID 생성
        if external_ids is None:
            external_ids = [f"doc_{self.next_id + i}" for i in range(n_vectors)]
        elif len(external_ids) != n_vectors:
            raise ValueError(f"External IDs count ({len(external_ids)}) != vectors count ({n_vectors})")
        
        # 중복 ID 검사
        duplicate_ids = set(external_ids) & set(self.external_to_id.keys())
        if duplicate_ids:
            raise ValueError(f"Duplicate external IDs found: {list(duplicate_ids)[:5]}...")
        
        # 메타데이터 검증
        if metadata and len(metadata) != n_vectors:
            raise ValueError(f"Metadata count ({len(metadata)}) != vectors count ({n_vectors})")
        
        # 삽입 전 인덱스 크기 기록
        initial_size = self.index.ntotal
        
        # 배치별 처리
        all_internal_ids = []
        
        for batch_start in range(0, n_vectors, batch_size):
            batch_end = min(batch_start + batch_size, n_vectors)
            batch_vectors = vectors[batch_start:batch_end]
            batch_external_ids = external_ids[batch_start:batch_end]
            batch_metadata = metadata[batch_start:batch_end] if metadata else None
            
            # 내부 ID 할당
            batch_size_actual = batch_end - batch_start
            internal_ids = list(range(self.next_id, self.next_id + batch_size_actual))
            
            # ID 매핑 업데이트
            for internal_id, external_id in zip(internal_ids, batch_external_ids):
                self.id_to_external[internal_id] = external_id
                self.external_to_id[external_id] = internal_id
            
            # 메타데이터 저장
            if batch_metadata:
                for internal_id, meta in zip(internal_ids, batch_metadata):
                    self.metadata[internal_id] = meta
            
            # 벡터 추가
            try:
                self.index.add_with_ids(batch_vectors, np.array(internal_ids, dtype=np.int64))
                self.next_id += batch_size_actual
                all_internal_ids.extend(internal_ids)
                
                logger.debug(f"Added batch {batch_start//batch_size + 1}: {batch_size_actual} vectors")
                
            except Exception as e:
                logger.error(f"Failed to add batch {batch_start//batch_size + 1}: {e}")
                # 롤백: 추가된 ID 매핑 제거
                for internal_id, external_id in zip(internal_ids, batch_external_ids):
                    self.id_to_external.pop(internal_id, None)
                    self.external_to_id.pop(external_id, None)
                    self.metadata.pop(internal_id, None)
                raise
        
        # 삽입 검증
        if verify_insertion:
            final_size = self.index.ntotal
            expected_size = initial_size + n_vectors
            
            if final_size != expected_size:
                logger.error(f"Index size mismatch: expected {expected_size}, got {final_size}")
                raise RuntimeError("Vector insertion verification failed")
        
        # 자동 저장
        if auto_save:
            self.save_index()
            logger.info("Index automatically saved to disk")
        
        logger.info(f"Successfully added {n_vectors} vectors in {len(range(0, n_vectors, batch_size))} batches")
        logger.info(f"Index total: {self.index.ntotal}, External IDs: {len(self.external_to_id)}")
        
        return all_internal_ids
    
    def save_index(self):
        """인덱스 및 메타데이터를 디스크에 저장"""
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        try:
            # FAISS 인덱스 저장
            index_path = self.data_dir / FAISSVectorStoreConfig.INDEX_FILE
            faiss.write_index(self.index, str(index_path))
            
            # ID 매핑 저장
            id_map_path = self.data_dir / FAISSVectorStoreConfig.ID_MAP_FILE
            with open(id_map_path, 'wb') as f:
                pickle.dump({
                    'id_to_external': self.id_to_external,
                    'external_to_id': self.external_to_id,
                    'next_id': self.next_id
                }, f)
            
            # 메타데이터 저장
            metadata_path = self.data_dir / FAISSVectorStoreConfig.METADATA_FILE
            metadata_info = {
                'created_at': datetime.now(UTC).isoformat(),
                'dimension': self.dimension,
                'nlist': self.nlist,
                'nprobe': self.nprobe,
                'hnsw_m': self.hnsw_m,
                'metric': self.metric,
                'ntotal': self.index.ntotal,
                'metadata': self.metadata
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata_info, f, indent=2)
            
            logger.info(f"Index saved successfully: {self.index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise
    
    def search(
        self, 
        query_vector, 
        top_k=5, 
        nprobe=None, 
        include_metadata=True,
        score_threshold=None,
        auto_nprobe=False
    ):
        """
        유사도 검색 - PRD 요구사항 구현 및 최적화
        
        Args:
            query_vector: 쿼리 벡터 (np.ndarray, shape: [dimension] or [1, dimension])
            top_k: 반환할 상위 결과 수 (기본: 5)
            nprobe: 검색할 클러스터 수 (None이면 기본값 사용)
            include_metadata: 메타데이터 포함 여부 (기본: True)
            score_threshold: 최소 유사도 점수 임계값 (선택적)
            auto_nprobe: nprobe 자동 조정 여부 (기본: False)
            
        Returns:
            Tuple[List[str], List[float], List[Dict]]: (external_ids, distances, metadata)
        """
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        if not self.is_trained():
            logger.warning("Index not trained")
            return [], [], []
        
        if self.index.ntotal == 0:
            logger.warning("Index is empty")
            return [], [], []
        
        # 입력 검증 및 전처리
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector)
        
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        elif query_vector.ndim != 2 or query_vector.shape[0] != 1:
            raise ValueError(f"Query vector must be 1D or 2D with shape [1, dim], got {query_vector.shape}")
        
        if query_vector.shape[1] != self.dimension:
            raise ValueError(f"Query dimension mismatch: expected {self.dimension}, got {query_vector.shape[1]}")
        
        query_vector = query_vector.astype(np.float32)
        
        # nprobe 자동 조정
        if auto_nprobe:
            nprobe = self._auto_adjust_nprobe(top_k)
            logger.debug(f"Auto-adjusted nprobe to {nprobe} for top_k={top_k}")
        
        # 임시 nprobe 설정
        original_nprobe = self.index.nprobe
        if nprobe is not None:
            if nprobe < 1 or nprobe > self.nlist:
                logger.warning(f"nprobe {nprobe} out of valid range [1, {self.nlist}], using default")
                nprobe = min(max(1, nprobe), self.nlist)
            self.index.nprobe = nprobe
        
        try:
            # FAISS 검색 수행
            distances, internal_ids = self.index.search(query_vector, top_k)
            
            # 결과 처리
            external_ids = []
            result_distances = []
            result_metadata = []
            
            for dist, internal_id in zip(distances[0], internal_ids[0]):
                if internal_id >= 0:  # 유효한 결과
                    # 점수 임계값 확인
                    if score_threshold is not None and dist > score_threshold:
                        continue
                    
                    external_id = self.id_to_external.get(internal_id)
                    if external_id:
                        external_ids.append(external_id)
                        result_distances.append(float(dist))
                        
                        if include_metadata:
                            result_metadata.append(self.metadata.get(internal_id, {}))
            
            # 메타데이터 없이 반환하는 경우
            if not include_metadata:
                result_metadata = []
            
            logger.debug(f"Search completed: {len(external_ids)}/{top_k} results returned")
            
            return external_ids, result_distances, result_metadata
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
            
        finally:
            # nprobe 복원
            self.index.nprobe = original_nprobe
    
    def _auto_adjust_nprobe(self, top_k):
        """
        top_k에 따른 nprobe 자동 조정
        
        Args:
            top_k: 요청된 결과 수
            
        Returns:
            int: 최적화된 nprobe 값
        """
        # 휴리스틱 기반 nprobe 조정
        if top_k <= 5:
            return min(16, self.nlist)
        elif top_k <= 20:
            return min(32, self.nlist)
        elif top_k <= 50:
            return min(64, self.nlist)
        else:
            return min(128, self.nlist)
    
    def batch_search(
        self, 
        query_vectors, 
        top_k=5, 
        nprobe=None, 
        include_metadata=True
    ):
        """
        배치 검색 - 여러 쿼리를 한 번에 처리
        
        Args:
            query_vectors: 쿼리 벡터 배열 (np.ndarray, shape: [n_queries, dimension])
            top_k: 각 쿼리당 반환할 결과 수
            nprobe: 검색할 클러스터 수
            include_metadata: 메타데이터 포함 여부
            
        Returns:
            List[Tuple]: 각 쿼리에 대한 (external_ids, distances, metadata) 튜플 리스트
        """
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        if not isinstance(query_vectors, np.ndarray):
            query_vectors = np.array(query_vectors)
        
        if query_vectors.ndim != 2:
            raise ValueError(f"Query vectors must be 2D array, got shape: {query_vectors.shape}")
        
        if query_vectors.shape[1] != self.dimension:
            raise ValueError(f"Query dimension mismatch: expected {self.dimension}, got {query_vectors.shape[1]}")
        
        query_vectors = query_vectors.astype(np.float32)
        n_queries = query_vectors.shape[0]
        
        # 임시 nprobe 설정
        original_nprobe = self.index.nprobe
        if nprobe is not None:
            self.index.nprobe = min(max(1, nprobe), self.nlist)
        
        try:
            # 배치 검색 수행
            distances, internal_ids = self.index.search(query_vectors, top_k)
            
            results = []
            
            for query_idx in range(n_queries):
                external_ids = []
                result_distances = []
                result_metadata = []
                
                for dist, internal_id in zip(distances[query_idx], internal_ids[query_idx]):
                    if internal_id >= 0:
                        external_id = self.id_to_external.get(internal_id)
                        if external_id:
                            external_ids.append(external_id)
                            result_distances.append(float(dist))
                            
                            if include_metadata:
                                result_metadata.append(self.metadata.get(internal_id, {}))
                
                if not include_metadata:
                    result_metadata = []
                
                results.append((external_ids, result_distances, result_metadata))
            
            logger.debug(f"Batch search completed: {n_queries} queries processed")
            
            return results
            
        finally:
            self.index.nprobe = original_nprobe
    
    def search_by_id(self, external_id, top_k=5, exclude_self=True):
        """
        ID로 검색 - 특정 문서와 유사한 문서 찾기
        
        Args:
            external_id: 기준 문서의 외부 ID
            top_k: 반환할 결과 수
            exclude_self: 자기 자신 제외 여부
            
        Returns:
            Tuple[List[str], List[float], List[Dict]]: (external_ids, distances, metadata)
        """
        if external_id not in self.external_to_id:
            raise ValueError(f"External ID not found: {external_id}")
        
        internal_id = self.external_to_id[external_id]
        
        # 해당 벡터 조회
        if hasattr(self.index, 'reconstruct'):
            try:
                query_vector = self.index.reconstruct(internal_id)
                query_vector = query_vector.reshape(1, -1)
            except:
                logger.error(f"Cannot reconstruct vector for ID {external_id}")
                return [], [], []
        else:
            logger.error("Index does not support vector reconstruction")
            return [], [], []
        
        # 검색 수행
        external_ids, distances, metadata = self.search(
            query_vector, 
            top_k=top_k + (1 if exclude_self else 0),
            include_metadata=True
        )
        
        # 자기 자신 제외
        if exclude_self and external_ids and external_ids[0] == external_id:
            external_ids = external_ids[1:]
            distances = distances[1:]
            metadata = metadata[1:]
        
        return external_ids[:top_k], distances[:top_k], metadata[:top_k]
    
    def get_index_stats(self):
        """인덱스 통계 정보 반환"""
        if self.index is None:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "is_trained": self.is_trained(),
            "ntotal": getattr(self.index, 'ntotal', 0),
            "dimension": self.dimension,
            "nlist": self.nlist,
            "nprobe": getattr(self.index, 'nprobe', None),
            "metric": self.metric,
            "hnsw_m": self.hnsw_m,
            "external_ids_count": len(self.external_to_id),
            "metadata_count": len(self.metadata)
        }


# 전역 벡터 스토어 인스턴스 (싱글톤 패턴)
_vector_store = None


def get_vector_store():
    """전역 벡터 스토어 인스턴스 반환"""
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
    return _vector_store


def reset_vector_store():
    """벡터 스토어 인스턴스 재설정 (테스트용)"""
    global _vector_store
    _vector_store = None
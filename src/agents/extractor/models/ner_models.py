"""
NER Model Manager

spaCy NER 모델들의 로딩 및 관리를 담당하는 모듈
"""

import logging
from typing import Dict, Optional, Any
from threading import Lock


class NERModelManager:
    """NER 모델 관리자"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """NERModelManager 초기화"""
        if not hasattr(self, '_initialized'):
            self.logger = logging.getLogger(__name__)
            self._models: Dict[str, Any] = {}
            self._model_info: Dict[str, dict] = {}
            self._load_lock = Lock()
            self._initialized = True
            
            # 지원되는 모델 정보
            self._supported_models = {
                "ko_core_news_sm": {
                    "description": "Korean small model (fast)",
                    "size": "small",
                    "performance": "fast",
                    "accuracy": "medium",
                    "memory_usage": "low"
                },
                "ko_core_news_lg": {
                    "description": "Korean large model (accurate)", 
                    "size": "large",
                    "performance": "slow",
                    "accuracy": "high",
                    "memory_usage": "high"
                }
            }
    
    def get_model(self, model_name: str):
        """
        모델을 가져옵니다. 필요시 지연 로딩합니다.
        
        Args:
            model_name: 모델 이름
            
        Returns:
            spaCy nlp 모델 객체
            
        Raises:
            ValueError: 지원되지 않는 모델
            RuntimeError: 모델 로딩 실패
        """
        if model_name not in self._supported_models:
            raise ValueError(f"지원되지 않는 모델: {model_name}")
            
        if model_name not in self._models:
            with self._load_lock:
                # 더블 체크 패턴
                if model_name not in self._models:
                    self._load_model(model_name)
                    
        return self._models[model_name]
    
    def _load_model(self, model_name: str):
        """
        모델을 실제로 로딩합니다.
        
        Args:
            model_name: 로딩할 모델 이름
            
        Raises:
            RuntimeError: 모델 로딩 실패
        """
        try:
            import spacy
            
            self.logger.info(f"spaCy 모델 '{model_name}' 로딩 시작...")
            nlp = spacy.load(model_name)
            
            # 모델 정보 저장
            self._models[model_name] = nlp
            self._model_info[model_name] = {
                "loaded_at": self._get_current_time(),
                "pipeline": nlp.pipe_names,
                "lang": nlp.lang,
                "vocab_size": len(nlp.vocab),
                **self._supported_models[model_name]
            }
            
            self.logger.info(f"spaCy 모델 '{model_name}' 로딩 완료")
            
        except Exception as e:
            error_msg = f"spaCy 모델 '{model_name}' 로딩 실패: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        모델이 로딩되어 있는지 확인합니다.
        
        Args:
            model_name: 확인할 모델 이름
            
        Returns:
            bool: 로딩 여부
        """
        return model_name in self._models
    
    def get_model_info(self, model_name: str) -> Optional[dict]:
        """
        모델 정보를 반환합니다.
        
        Args:
            model_name: 모델 이름
            
        Returns:
            Optional[dict]: 모델 정보 (없으면 None)
        """
        if model_name in self._model_info:
            return self._model_info[model_name].copy()
        elif model_name in self._supported_models:
            return self._supported_models[model_name].copy()
        else:
            return None
    
    def get_supported_models(self) -> Dict[str, dict]:
        """
        지원되는 모델 목록을 반환합니다.
        
        Returns:
            Dict[str, dict]: 지원 모델 정보
        """
        return self._supported_models.copy()
    
    def get_loaded_models(self) -> Dict[str, dict]:
        """
        현재 로딩된 모델 목록을 반환합니다.
        
        Returns:
            Dict[str, dict]: 로딩된 모델 정보
        """
        return {name: info.copy() for name, info in self._model_info.items()}
    
    def unload_model(self, model_name: str) -> bool:
        """
        모델을 메모리에서 언로드합니다.
        
        Args:
            model_name: 언로드할 모델 이름
            
        Returns:
            bool: 성공 여부
        """
        if model_name in self._models:
            with self._load_lock:
                if model_name in self._models:
                    del self._models[model_name]
                    del self._model_info[model_name]
                    self.logger.info(f"spaCy 모델 '{model_name}' 언로드 완료")
                    return True
        return False
    
    def unload_all_models(self):
        """모든 모델을 언로드합니다."""
        with self._load_lock:
            model_names = list(self._models.keys())
            for model_name in model_names:
                self.unload_model(model_name)
            self.logger.info("모든 spaCy 모델 언로드 완료")
    
    def get_memory_usage(self) -> dict:
        """
        현재 메모리 사용량 정보를 반환합니다.
        
        Returns:
            dict: 메모리 사용량 정보
        """
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "total_memory_mb": memory_info.rss / 1024 / 1024,
                "loaded_models_count": len(self._models),
                "loaded_models": list(self._models.keys())
            }
        except ImportError:
            return {
                "error": "psutil not installed",
                "loaded_models_count": len(self._models),
                "loaded_models": list(self._models.keys())
            }
    
    def _get_current_time(self) -> str:
        """현재 시간을 ISO 형식으로 반환합니다."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def health_check(self) -> dict:
        """
        모델 관리자 상태를 확인합니다.
        
        Returns:
            dict: 상태 정보
        """
        try:
            status = "healthy"
            issues = []
            
            # spaCy 설치 확인
            try:
                import spacy
                spacy_version = spacy.__version__
            except ImportError:
                status = "unhealthy"
                issues.append("spaCy not installed")
                spacy_version = "not_available"
            
            # 지원 모델 설치 확인
            available_models = []
            for model_name in self._supported_models.keys():
                try:
                    import spacy
                    spacy.load(model_name)
                    available_models.append(model_name)
                except Exception:
                    issues.append(f"Model '{model_name}' not available")
            
            if not available_models:
                status = "unhealthy"
                issues.append("No supported models available")
            
            return {
                "status": status,
                "spacy_version": spacy_version,
                "supported_models": list(self._supported_models.keys()),
                "available_models": available_models,
                "loaded_models": list(self._models.keys()),
                "issues": issues,
                "memory_usage": self.get_memory_usage()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "loaded_models": list(self._models.keys())
            }
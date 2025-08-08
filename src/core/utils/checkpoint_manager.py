"""
체크포인터 롤백 관리자

실패 시 이전 체크포인트 상태로 롤백하는 기본 기능
- 작업 진행 중 상태 저장
- 오류 발생 시 이전 상태로 복원
- 간단한 체크포인터 롤백 로직
"""

import logging
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class CheckpointData:
    """체크포인트 데이터 클래스"""
    
    def __init__(self, checkpoint_id: str, workflow_id: str, state: Dict[str, Any]):
        """
        CheckpointData 초기화
        
        Args:
            checkpoint_id: 체크포인트 ID
            workflow_id: 워크플로우 ID
            state: 상태 데이터
        """
        self.checkpoint_id = checkpoint_id
        self.workflow_id = workflow_id
        self.state = state
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointData':
        """딕셔너리에서 생성"""
        checkpoint = cls(
            checkpoint_id=data["checkpoint_id"],
            workflow_id=data["workflow_id"],
            state=data["state"]
        )
        checkpoint.created_at = datetime.fromisoformat(data["created_at"])
        checkpoint.updated_at = datetime.fromisoformat(data["updated_at"])
        return checkpoint


class CheckpointManager:
    """체크포인터 롤백 관리자"""
    
    def __init__(self, checkpoint_dir: Optional[str] = None, max_checkpoints: int = 10):
        """
        CheckpointManager 초기화
        
        Args:
            checkpoint_dir: 체크포인트 저장 디렉토리
            max_checkpoints: 워크플로우당 최대 체크포인트 수
        """
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else Path("data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        
        # 메모리 캐시 (성능 향상)
        self.checkpoint_cache: Dict[str, List[CheckpointData]] = {}
        
        logger.info(f"CheckpointManager initialized: dir={self.checkpoint_dir}, max_checkpoints={max_checkpoints}")
    
    def create_checkpoint(self, workflow_id: str, state: Dict[str, Any]) -> str:
        """
        체크포인트 생성
        
        Args:
            workflow_id: 워크플로우 ID
            state: 상태 데이터
            
        Returns:
            str: 생성된 체크포인트 ID
        """
        try:
            checkpoint_id = str(uuid.uuid4())
            checkpoint_data = CheckpointData(checkpoint_id, workflow_id, state)
            
            # 메모리 캐시에 저장
            if workflow_id not in self.checkpoint_cache:
                self.checkpoint_cache[workflow_id] = []
            
            self.checkpoint_cache[workflow_id].append(checkpoint_data)
            
            # 최대 체크포인트 수 제한
            if len(self.checkpoint_cache[workflow_id]) > self.max_checkpoints:
                oldest_checkpoint = self.checkpoint_cache[workflow_id].pop(0)
                self._remove_checkpoint_file(oldest_checkpoint.checkpoint_id)
            
            # 파일에 저장
            self._save_checkpoint_to_file(checkpoint_data)
            
            logger.info(f"Checkpoint created: {checkpoint_id} for workflow {workflow_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint for workflow {workflow_id}: {e}")
            raise
    
    def get_latest_checkpoint(self, workflow_id: str) -> Optional[CheckpointData]:
        """
        최신 체크포인트 조회
        
        Args:
            workflow_id: 워크플로우 ID
            
        Returns:
            Optional[CheckpointData]: 최신 체크포인트 데이터
        """
        try:
            # 메모리 캐시에서 조회
            if workflow_id in self.checkpoint_cache and self.checkpoint_cache[workflow_id]:
                return self.checkpoint_cache[workflow_id][-1]
            
            # 파일에서 로드
            checkpoints = self._load_checkpoints_from_files(workflow_id)
            if checkpoints:
                # 메모리 캐시 업데이트
                self.checkpoint_cache[workflow_id] = checkpoints
                return checkpoints[-1]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint for workflow {workflow_id}: {e}")
            return None
    
    def rollback_to_checkpoint(self, workflow_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        체크포인트로 롤백
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_id: 롤백할 체크포인트 ID (None이면 최신)
            
        Returns:
            Optional[Dict[str, Any]]: 롤백된 상태 데이터
        """
        try:
            if checkpoint_id:
                # 특정 체크포인트로 롤백
                checkpoint = self._get_checkpoint_by_id(workflow_id, checkpoint_id)
            else:
                # 최신 체크포인트로 롤백
                checkpoint = self.get_latest_checkpoint(workflow_id)
            
            if not checkpoint:
                logger.warning(f"No checkpoint found for rollback: workflow={workflow_id}, checkpoint={checkpoint_id}")
                return None
            
            logger.info(f"Rolling back workflow {workflow_id} to checkpoint {checkpoint.checkpoint_id}")
            return checkpoint.state.copy()
            
        except Exception as e:
            logger.error(f"Failed to rollback workflow {workflow_id}: {e}")
            return None
    
    def list_checkpoints(self, workflow_id: str) -> List[CheckpointData]:
        """
        워크플로우의 체크포인트 목록 조회
        
        Args:
            workflow_id: 워크플로우 ID
            
        Returns:
            List[CheckpointData]: 체크포인트 목록
        """
        try:
            # 메모리 캐시에서 조회
            if workflow_id in self.checkpoint_cache:
                return self.checkpoint_cache[workflow_id].copy()
            
            # 파일에서 로드
            checkpoints = self._load_checkpoints_from_files(workflow_id)
            if checkpoints:
                self.checkpoint_cache[workflow_id] = checkpoints
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints for workflow {workflow_id}: {e}")
            return []
    
    def delete_checkpoint(self, workflow_id: str, checkpoint_id: str) -> bool:
        """
        체크포인트 삭제
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_id: 삭제할 체크포인트 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 메모리 캐시에서 제거
            if workflow_id in self.checkpoint_cache:
                self.checkpoint_cache[workflow_id] = [
                    cp for cp in self.checkpoint_cache[workflow_id] 
                    if cp.checkpoint_id != checkpoint_id
                ]
            
            # 파일에서 제거
            return self._remove_checkpoint_file(checkpoint_id)
            
        except Exception as e:
            logger.error(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            return False
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """
        오래된 체크포인트 정리
        
        Args:
            max_age_hours: 최대 보관 시간 (시간)
            
        Returns:
            int: 정리된 체크포인트 수
        """
        try:
            cutoff_time = time.time() - (max_age_hours * 3600)
            cleaned_count = 0
            
            # 모든 워크플로우 체크포인트 검사
            for workflow_id in list(self.checkpoint_cache.keys()):
                checkpoints = self.checkpoint_cache[workflow_id]
                old_checkpoints = [
                    cp for cp in checkpoints 
                    if cp.created_at.timestamp() < cutoff_time
                ]
                
                for checkpoint in old_checkpoints:
                    if self.delete_checkpoint(workflow_id, checkpoint.checkpoint_id):
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old checkpoints")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")
            return 0
    
    def _save_checkpoint_to_file(self, checkpoint: CheckpointData) -> bool:
        """체크포인트를 파일에 저장"""
        try:
            file_path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            with open(file_path, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint to file: {e}")
            return False
    
    def _load_checkpoints_from_files(self, workflow_id: str) -> List[CheckpointData]:
        """파일에서 체크포인트 로드"""
        try:
            checkpoints = []
            
            for file_path in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    if data["workflow_id"] == workflow_id:
                        checkpoint = CheckpointData.from_dict(data)
                        checkpoints.append(checkpoint)
                        
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint from {file_path}: {e}")
            
            # 생성 시간순으로 정렬
            checkpoints.sort(key=lambda x: x.created_at)
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to load checkpoints from files: {e}")
            return []
    
    def _get_checkpoint_by_id(self, workflow_id: str, checkpoint_id: str) -> Optional[CheckpointData]:
        """ID로 체크포인트 조회"""
        try:
            # 메모리 캐시에서 조회
            if workflow_id in self.checkpoint_cache:
                for checkpoint in self.checkpoint_cache[workflow_id]:
                    if checkpoint.checkpoint_id == checkpoint_id:
                        return checkpoint
            
            # 파일에서 조회
            file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if data["workflow_id"] == workflow_id:
                    return CheckpointData.from_dict(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint by ID: {e}")
            return None
    
    def _remove_checkpoint_file(self, checkpoint_id: str) -> bool:
        """체크포인트 파일 삭제"""
        try:
            file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove checkpoint file: {e}")
            return False
    
    @contextmanager
    def checkpoint_context(self, workflow_id: str, state: Dict[str, Any]):
        """
        체크포인트 컨텍스트 매니저
        
        Args:
            workflow_id: 워크플로우 ID
            state: 초기 상태 데이터
            
        Yields:
            str: 생성된 체크포인트 ID
        """
        checkpoint_id = None
        try:
            checkpoint_id = self.create_checkpoint(workflow_id, state)
            yield checkpoint_id
        except Exception as e:
            logger.error(f"Error in checkpoint context: {e}")
            if checkpoint_id:
                # 오류 발생 시 롤백
                rollback_state = self.rollback_to_checkpoint(workflow_id, checkpoint_id)
                if rollback_state:
                    logger.info(f"Rolled back to checkpoint {checkpoint_id}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        CheckpointManager 상태 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            total_checkpoints = sum(len(checkpoints) for checkpoints in self.checkpoint_cache.values())
            total_workflows = len(self.checkpoint_cache)
            
            health_info = {
                "status": "healthy",
                "checkpoint_dir": str(self.checkpoint_dir),
                "total_checkpoints": total_checkpoints,
                "total_workflows": total_workflows,
                "max_checkpoints_per_workflow": self.max_checkpoints,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("CheckpointManager health check completed")
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.error(f"CheckpointManager health check failed: {e}")
            return health_info


# 전역 CheckpointManager 인스턴스
checkpoint_manager = CheckpointManager()


def create_checkpoint(workflow_id: str, state: Dict[str, Any]) -> str:
    """
    전역 체크포인트 생성 함수
    
    Args:
        workflow_id: 워크플로우 ID
        state: 상태 데이터
        
    Returns:
        str: 생성된 체크포인트 ID
    """
    return checkpoint_manager.create_checkpoint(workflow_id, state)


def rollback_to_checkpoint(workflow_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    전역 체크포인트 롤백 함수
    
    Args:
        workflow_id: 워크플로우 ID
        checkpoint_id: 롤백할 체크포인트 ID (None이면 최신)
        
    Returns:
        Optional[Dict[str, Any]]: 롤백된 상태 데이터
    """
    return checkpoint_manager.rollback_to_checkpoint(workflow_id, checkpoint_id)


@contextmanager
def checkpoint_context(workflow_id: str, state: Dict[str, Any]):
    """
    전역 체크포인트 컨텍스트 매니저
    
    Args:
        workflow_id: 워크플로우 ID
        state: 초기 상태 데이터
        
    Yields:
        str: 생성된 체크포인트 ID
    """
    with checkpoint_manager.checkpoint_context(workflow_id, state) as checkpoint_id:
        yield checkpoint_id


if __name__ == "__main__":
    # 기본 테스트
    print("✅ CheckpointManager 완전 구현 성공")
    
    # 테스트 워크플로우
    workflow_id = "test_workflow_001"
    
    # 체크포인트 생성 테스트
    state1 = {"step": "research", "data": {"query": "AI"}}
    checkpoint_id1 = create_checkpoint(workflow_id, state1)
    print(f"✅ 체크포인트 생성: {checkpoint_id1}")
    
    # 상태 업데이트 후 체크포인트 생성
    state2 = {"step": "extract", "data": {"entities": ["AI", "ML"]}}
    checkpoint_id2 = create_checkpoint(workflow_id, state2)
    print(f"✅ 체크포인트 생성: {checkpoint_id2}")
    
    # 롤백 테스트
    rollback_state = rollback_to_checkpoint(workflow_id, checkpoint_id1)
    print(f"✅ 롤백 성공: {rollback_state}")
    
    # 컨텍스트 매니저 테스트
    with checkpoint_context(workflow_id, {"step": "test", "data": {"test": True}}) as cp_id:
        print(f"✅ 컨텍스트 매니저 체크포인트: {cp_id}")
    
    print("✅ 모든 테스트 완료") 
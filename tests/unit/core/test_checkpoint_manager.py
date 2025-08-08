"""
CheckpointManager 단위 테스트

체크포인터 롤백 관리자 테스트
- 체크포인트 생성 및 조회
- 롤백 기능
- 컨텍스트 매니저
- 파일 저장 및 로드
"""

import pytest
import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from src.core.utils.checkpoint_manager import (
    CheckpointManager,
    CheckpointData,
    create_checkpoint,
    rollback_to_checkpoint,
    checkpoint_context
)


class TestCheckpointData:
    """CheckpointData 테스트 클래스"""
    
    def test_checkpoint_data_initialization(self):
        """CheckpointData 초기화 테스트"""
        checkpoint_id = str(uuid.uuid4())
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        checkpoint = CheckpointData(checkpoint_id, workflow_id, state)
        
        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.workflow_id == workflow_id
        assert checkpoint.state == state
        assert isinstance(checkpoint.created_at, datetime)
        assert isinstance(checkpoint.updated_at, datetime)
    
    def test_checkpoint_data_to_dict(self):
        """CheckpointData to_dict 메서드 테스트"""
        checkpoint_id = str(uuid.uuid4())
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        checkpoint = CheckpointData(checkpoint_id, workflow_id, state)
        data_dict = checkpoint.to_dict()
        
        assert data_dict["checkpoint_id"] == checkpoint_id
        assert data_dict["workflow_id"] == workflow_id
        assert data_dict["state"] == state
        assert "created_at" in data_dict
        assert "updated_at" in data_dict
    
    def test_checkpoint_data_from_dict(self):
        """CheckpointData from_dict 메서드 테스트"""
        checkpoint_id = str(uuid.uuid4())
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        created_at = datetime.now().isoformat()
        updated_at = datetime.now().isoformat()
        
        data_dict = {
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow_id,
            "state": state,
            "created_at": created_at,
            "updated_at": updated_at
        }
        
        checkpoint = CheckpointData.from_dict(data_dict)
        
        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.workflow_id == workflow_id
        assert checkpoint.state == state
        assert checkpoint.created_at.isoformat() == created_at
        assert checkpoint.updated_at.isoformat() == updated_at


class TestCheckpointManager:
    """CheckpointManager 테스트 클래스"""
    
    @pytest.fixture
    def checkpoint_manager(self, tmp_path):
        """CheckpointManager 인스턴스 생성"""
        checkpoint_dir = tmp_path / "checkpoints"
        return CheckpointManager(checkpoint_dir=str(checkpoint_dir), max_checkpoints=5)
    
    def test_checkpoint_manager_initialization(self, checkpoint_manager):
        """CheckpointManager 초기화 테스트"""
        assert checkpoint_manager.checkpoint_dir.exists()
        assert checkpoint_manager.max_checkpoints == 5
        assert isinstance(checkpoint_manager.checkpoint_cache, dict)
        assert len(checkpoint_manager.checkpoint_cache) == 0
    
    def test_create_checkpoint(self, checkpoint_manager):
        """체크포인트 생성 테스트"""
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
        
        assert checkpoint_id is not None
        assert isinstance(checkpoint_id, str)
        assert workflow_id in checkpoint_manager.checkpoint_cache
        assert len(checkpoint_manager.checkpoint_cache[workflow_id]) == 1
        
        checkpoint = checkpoint_manager.checkpoint_cache[workflow_id][0]
        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.workflow_id == workflow_id
        assert checkpoint.state == state
    
    def test_create_multiple_checkpoints(self, checkpoint_manager):
        """여러 체크포인트 생성 테스트"""
        workflow_id = "test_workflow"
        
        # 여러 체크포인트 생성
        checkpoint_ids = []
        for i in range(3):
            state = {"step": f"step_{i}", "data": f"data_{i}"}
            checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
            checkpoint_ids.append(checkpoint_id)
        
        assert len(checkpoint_manager.checkpoint_cache[workflow_id]) == 3
        assert len(checkpoint_ids) == 3
        assert len(set(checkpoint_ids)) == 3  # 모든 ID가 고유해야 함
    
    def test_get_latest_checkpoint(self, checkpoint_manager):
        """최신 체크포인트 조회 테스트"""
        workflow_id = "test_workflow"
        
        # 체크포인트가 없는 경우
        latest = checkpoint_manager.get_latest_checkpoint(workflow_id)
        assert latest is None
        
        # 체크포인트 생성
        state1 = {"step": "step_1", "data": "data_1"}
        checkpoint_id1 = checkpoint_manager.create_checkpoint(workflow_id, state1)
        
        time.sleep(0.1)  # 시간 차이를 위해 잠시 대기
        
        state2 = {"step": "step_2", "data": "data_2"}
        checkpoint_id2 = checkpoint_manager.create_checkpoint(workflow_id, state2)
        
        # 최신 체크포인트 조회
        latest = checkpoint_manager.get_latest_checkpoint(workflow_id)
        
        assert latest is not None
        assert latest.checkpoint_id == checkpoint_id2
        assert latest.state == state2
    
    def test_rollback_to_checkpoint(self, checkpoint_manager):
        """체크포인트로 롤백 테스트"""
        workflow_id = "test_workflow"
        
        # 여러 체크포인트 생성
        states = []
        checkpoint_ids = []
        for i in range(3):
            state = {"step": f"step_{i}", "data": f"data_{i}"}
            states.append(state)
            checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
            checkpoint_ids.append(checkpoint_id)
        
        # 특정 체크포인트로 롤백
        rollback_state = checkpoint_manager.rollback_to_checkpoint(workflow_id, checkpoint_ids[1])
        
        assert rollback_state is not None
        assert rollback_state == states[1]
    
    def test_rollback_to_latest_checkpoint(self, checkpoint_manager):
        """최신 체크포인트로 롤백 테스트"""
        workflow_id = "test_workflow"
        
        # 체크포인트 생성
        state = {"step": "test", "data": "test_data"}
        checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 최신 체크포인트로 롤백 (checkpoint_id=None)
        rollback_state = checkpoint_manager.rollback_to_checkpoint(workflow_id)
        
        assert rollback_state is not None
        assert rollback_state == state
    
    def test_rollback_to_nonexistent_checkpoint(self, checkpoint_manager):
        """존재하지 않는 체크포인트로 롤백 테스트"""
        workflow_id = "test_workflow"
        nonexistent_id = str(uuid.uuid4())
        
        rollback_state = checkpoint_manager.rollback_to_checkpoint(workflow_id, nonexistent_id)
        
        assert rollback_state is None
    
    def test_list_checkpoints(self, checkpoint_manager):
        """체크포인트 목록 조회 테스트"""
        workflow_id = "test_workflow"
        
        # 초기 상태
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 0
        
        # 여러 체크포인트 생성
        for i in range(3):
            state = {"step": f"step_{i}", "data": f"data_{i}"}
            checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 체크포인트 목록 조회
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 3
        
        # 생성 시간 순으로 정렬되어 있어야 함 (최신이 마지막)
        for i, checkpoint in enumerate(checkpoints):
            assert checkpoint.state["step"] == f"step_{i}"
    
    def test_delete_checkpoint(self, checkpoint_manager):
        """체크포인트 삭제 테스트"""
        workflow_id = "test_workflow"
        
        # 체크포인트 생성
        state = {"step": "test", "data": "test_data"}
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 체크포인트 삭제
        result = checkpoint_manager.delete_checkpoint(workflow_id, checkpoint_id)
        
        assert result is True
        assert len(checkpoint_manager.checkpoint_cache[workflow_id]) == 0
    
    def test_delete_nonexistent_checkpoint(self, checkpoint_manager):
        """존재하지 않는 체크포인트 삭제 테스트"""
        workflow_id = "test_workflow"
        nonexistent_id = str(uuid.uuid4())
        
        result = checkpoint_manager.delete_checkpoint(workflow_id, nonexistent_id)
        
        assert result is False
    
    def test_max_checkpoints_limit(self, checkpoint_manager):
        """최대 체크포인트 수 제한 테스트"""
        workflow_id = "test_workflow"
        max_checkpoints = checkpoint_manager.max_checkpoints
        
        # 최대 개수보다 많은 체크포인트 생성
        for i in range(max_checkpoints + 2):
            state = {"step": f"step_{i}", "data": f"data_{i}"}
            checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 최대 개수만큼만 유지되어야 함
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == max_checkpoints
        
        # 가장 오래된 체크포인트가 삭제되어야 함
        assert checkpoints[0].state["step"] == "step_2"  # step_0, step_1이 삭제됨
    
    def test_cleanup_old_checkpoints(self, checkpoint_manager):
        """오래된 체크포인트 정리 테스트"""
        workflow_id = "test_workflow"
        
        # 체크포인트 생성
        state = {"step": "test", "data": "test_data"}
        checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 오래된 체크포인트로 수정 시간 변경
        checkpoint = checkpoint_manager.checkpoint_cache[workflow_id][0]
        old_time = datetime.now() - timedelta(hours=25)
        checkpoint.updated_at = old_time
        
        # 정리 실행
        cleaned_count = checkpoint_manager.cleanup_old_checkpoints(max_age_hours=24)
        
        assert cleaned_count >= 1
        assert len(checkpoint_manager.checkpoint_cache[workflow_id]) == 0
    
    def test_checkpoint_context_manager(self, checkpoint_manager):
        """체크포인트 컨텍스트 매니저 테스트"""
        workflow_id = "test_workflow"
        initial_state = {"step": "initial", "data": "initial_data"}
        
        with checkpoint_manager.checkpoint_context(workflow_id, initial_state):
            # 컨텍스트 내에서 체크포인트가 생성되어야 함
            checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
            assert len(checkpoints) == 1
            assert checkpoints[0].state == initial_state
        
        # 컨텍스트 종료 후에도 체크포인트가 유지되어야 함
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 1
    
    def test_checkpoint_context_with_exception(self, checkpoint_manager):
        """예외 발생 시 체크포인트 컨텍스트 매니저 테스트"""
        workflow_id = "test_workflow"
        initial_state = {"step": "initial", "data": "initial_data"}
        
        try:
            with checkpoint_manager.checkpoint_context(workflow_id, initial_state):
                # 컨텍스트 내에서 예외 발생
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # 예외 발생 후에도 체크포인트가 유지되어야 함
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == 1
        assert checkpoints[0].state == initial_state
    
    def test_health_check(self, checkpoint_manager):
        """상태 확인 테스트"""
        health_info = checkpoint_manager.health_check()
        
        assert health_info["status"] == "healthy"
        assert health_info["checkpoint_dir"] == str(checkpoint_manager.checkpoint_dir)
        assert "total_workflows" in health_info
        assert "total_checkpoints" in health_info
        assert "max_checkpoints" in health_info
        assert health_info["max_checkpoints"] == checkpoint_manager.max_checkpoints
    
    def test_file_save_and_load(self, checkpoint_manager):
        """파일 저장 및 로드 테스트"""
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        # 체크포인트 생성
        checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 파일에 저장되었는지 확인
        checkpoint_file = checkpoint_manager.checkpoint_dir / f"{checkpoint_id}.json"
        assert checkpoint_file.exists()
        
        # 파일 내용 확인
        with open(checkpoint_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["checkpoint_id"] == checkpoint_id
        assert saved_data["workflow_id"] == workflow_id
        assert saved_data["state"] == state
    
    def test_load_checkpoints_from_files(self, checkpoint_manager):
        """파일에서 체크포인트 로드 테스트"""
        workflow_id = "test_workflow"
        
        # 캐시를 비우고 파일에서 로드
        checkpoint_manager.checkpoint_cache.clear()
        
        # 파일에서 체크포인트 로드
        checkpoints = checkpoint_manager._load_checkpoints_from_files(workflow_id)
        
        # 파일이 없으면 빈 리스트 반환
        assert isinstance(checkpoints, list)


class TestGlobalFunctions:
    """전역 함수 테스트 클래스"""
    
    @pytest.fixture
    def temp_checkpoint_dir(self, tmp_path):
        """임시 체크포인트 디렉토리 생성"""
        checkpoint_dir = tmp_path / "global_checkpoints"
        checkpoint_dir.mkdir()
        return checkpoint_dir
    
    def test_create_checkpoint_global(self, temp_checkpoint_dir):
        """전역 create_checkpoint 함수 테스트"""
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        with patch('src.core.utils.checkpoint_manager.CheckpointManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.create_checkpoint.return_value = "test_checkpoint_id"
            
            checkpoint_id = create_checkpoint(workflow_id, state)
            
            mock_manager.create_checkpoint.assert_called_once_with(workflow_id, state)
            assert checkpoint_id == "test_checkpoint_id"
    
    def test_rollback_to_checkpoint_global(self, temp_checkpoint_dir):
        """전역 rollback_to_checkpoint 함수 테스트"""
        workflow_id = "test_workflow"
        checkpoint_id = "test_checkpoint_id"
        expected_state = {"step": "test", "data": "test_data"}
        
        with patch('src.core.utils.checkpoint_manager.CheckpointManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.rollback_to_checkpoint.return_value = expected_state
            
            rollback_state = rollback_to_checkpoint(workflow_id, checkpoint_id)
            
            mock_manager.rollback_to_checkpoint.assert_called_once_with(workflow_id, checkpoint_id)
            assert rollback_state == expected_state
    
    def test_checkpoint_context_global(self, temp_checkpoint_dir):
        """전역 checkpoint_context 함수 테스트"""
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        
        with patch('src.core.utils.checkpoint_manager.CheckpointManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            with checkpoint_context(workflow_id, state):
                pass
            
            # checkpoint_context가 호출되었는지 확인
            assert mock_manager.checkpoint_context.called


class TestCheckpointManagerIntegration:
    """CheckpointManager 통합 테스트"""
    
    def test_workflow_with_checkpoints(self, tmp_path):
        """워크플로우와 함께 체크포인트 사용 테스트"""
        checkpoint_manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"))
        workflow_id = "test_workflow"
        
        # 워크플로우 단계별 체크포인트 생성
        steps = ["research", "extract", "retrieve", "wiki", "graphviz"]
        checkpoint_ids = []
        
        for step in steps:
            state = {
                "current_step": step,
                "steps_completed": steps[:steps.index(step)],
                "data": {f"{step}_data": f"data_for_{step}"}
            }
            checkpoint_id = checkpoint_manager.create_checkpoint(workflow_id, state)
            checkpoint_ids.append(checkpoint_id)
        
        # 모든 체크포인트 확인
        checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
        assert len(checkpoints) == len(steps)
        
        # 중간 단계로 롤백
        rollback_state = checkpoint_manager.rollback_to_checkpoint(workflow_id, checkpoint_ids[2])
        assert rollback_state["current_step"] == "retrieve"
        assert len(rollback_state["steps_completed"]) == 2
        
        # 최신 체크포인트로 롤백
        latest_state = checkpoint_manager.rollback_to_checkpoint(workflow_id)
        assert latest_state["current_step"] == "graphviz"
        assert len(latest_state["steps_completed"]) == 4
    
    def test_multiple_workflows(self, tmp_path):
        """여러 워크플로우 체크포인트 관리 테스트"""
        checkpoint_manager = CheckpointManager(checkpoint_dir=str(tmp_path / "checkpoints"))
        
        # 여러 워크플로우에 체크포인트 생성
        workflows = ["workflow_1", "workflow_2", "workflow_3"]
        
        for workflow_id in workflows:
            state = {"workflow_id": workflow_id, "status": "running"}
            checkpoint_manager.create_checkpoint(workflow_id, state)
        
        # 각 워크플로우의 체크포인트 확인
        for workflow_id in workflows:
            checkpoints = checkpoint_manager.list_checkpoints(workflow_id)
            assert len(checkpoints) == 1
            assert checkpoints[0].state["workflow_id"] == workflow_id
    
    def test_checkpoint_persistence(self, tmp_path):
        """체크포인트 지속성 테스트"""
        checkpoint_dir = tmp_path / "checkpoints"
        
        # 첫 번째 매니저로 체크포인트 생성
        manager1 = CheckpointManager(checkpoint_dir=str(checkpoint_dir))
        workflow_id = "test_workflow"
        state = {"step": "test", "data": "test_data"}
        checkpoint_id = manager1.create_checkpoint(workflow_id, state)
        
        # 두 번째 매니저로 체크포인트 로드
        manager2 = CheckpointManager(checkpoint_dir=str(checkpoint_dir))
        loaded_checkpoints = manager2.list_checkpoints(workflow_id)
        
        assert len(loaded_checkpoints) == 1
        assert loaded_checkpoints[0].checkpoint_id == checkpoint_id
        assert loaded_checkpoints[0].state == state 
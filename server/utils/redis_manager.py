"""
Redis 연결 관리 및 스냅샷 저장 유틸리티

PRD 요구사항에 따른 Redis-JSON 기반 상태 스냅샷 저장/조회 기능
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis
from pydantic import BaseModel

# aioredis import 오류 임시 해결
try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except (ImportError, TypeError) as e:
    AIOREDIS_AVAILABLE = False
    aioredis = None
    logging.warning(f"aioredis 사용 불가: {e}")

from server.schemas.base import WorkflowState, CheckpointData, MessageBase

logger = logging.getLogger(__name__)


class RedisConfig(BaseModel):
    """Redis 연결 설정"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True


class RedisManager:
    """
    Redis 연결 관리자
    
    동기/비동기 Redis 클라이언트 관리 및 연결 상태 모니터링
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        
    def get_sync_client(self) -> redis.Redis:
        """동기 Redis 클라이언트 반환"""
        if self._sync_client is None:
            self._connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=True
            )
            self._sync_client = redis.Redis(connection_pool=self._connection_pool)
        return self._sync_client
    
    async def get_async_client(self):
        """비동기 Redis 클라이언트 반환"""
        if not AIOREDIS_AVAILABLE:
            raise RuntimeError("aioredis가 사용 불가능합니다")
        
        if self._async_client is None:
            self._async_client = await aioredis.from_url(
                f"redis://{self.config.host}:{self.config.port}/{self.config.db}",
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=True
            )
        return self._async_client
    
    def test_connection(self) -> bool:
        """Redis 연결 테스트"""
        try:
            client = self.get_sync_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            return False
    
    async def test_async_connection(self) -> bool:
        """비동기 Redis 연결 테스트"""
        try:
            client = await self.get_async_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"비동기 Redis 연결 실패: {e}")
            return False
    
    def close(self):
        """연결 종료"""
        if self._sync_client:
            self._sync_client.close()
        if self._connection_pool:
            self._connection_pool.disconnect()
    
    async def close_async(self):
        """비동기 연결 종료"""
        if self._async_client:
            await self._async_client.close()


class SnapshotManager:
    """
    스냅샷 저장 관리자
    
    PRD 요구사항에 따른 Redis-JSON 기반 워크플로우 상태 스냅샷 저장/조회
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.key_prefix = "kg_checkpoint"
        self.default_ttl = 86400 * 7  # 7일
        
    def _generate_key(self, trace_id: str, checkpoint_type: str = "snapshot") -> str:
        """스냅샷 키 생성"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{self.key_prefix}:{trace_id}:{checkpoint_type}:{timestamp}"
    
    def _generate_latest_key(self, trace_id: str) -> str:
        """최신 스냅샷 키 생성"""
        return f"{self.key_prefix}:{trace_id}:latest"
    
    def save_checkpoint(
        self,
        checkpoint_data: CheckpointData,
        ttl: Optional[int] = None
    ) -> str:
        """
        체크포인트 저장 (동기)
        
        Args:
            checkpoint_data: 저장할 체크포인트 데이터
            ttl: TTL (초), None이면 기본값 사용
            
        Returns:
            str: 저장된 키
        """
        try:
            client = self.redis_manager.get_sync_client()
            
            # 키 생성
            key = self._generate_key(
                checkpoint_data.workflow_id, 
                checkpoint_data.checkpoint_type
            )
            latest_key = self._generate_latest_key(checkpoint_data.workflow_id)
            
            # JSON 직렬화
            data = checkpoint_data.model_dump_json()
            
            # Redis에 저장
            client.set(key, data, ex=ttl or self.default_ttl)
            client.set(latest_key, key, ex=ttl or self.default_ttl)
            
            logger.info(f"체크포인트 저장 완료: {key}")
            return key
            
        except Exception as e:
            logger.error(f"체크포인트 저장 실패: {e}")
            raise
    
    async def save_checkpoint_async(
        self,
        checkpoint_data: CheckpointData,
        ttl: Optional[int] = None
    ) -> str:
        """
        체크포인트 저장 (비동기)
        
        Args:
            checkpoint_data: 저장할 체크포인트 데이터
            ttl: TTL (초), None이면 기본값 사용
            
        Returns:
            str: 저장된 키
        """
        try:
            client = await self.redis_manager.get_async_client()
            
            # 키 생성
            key = self._generate_key(
                checkpoint_data.workflow_id,
                checkpoint_data.checkpoint_type
            )
            latest_key = self._generate_latest_key(checkpoint_data.workflow_id)
            
            # JSON 직렬화
            data = checkpoint_data.model_dump_json()
            
            # Redis에 저장
            await client.set(key, data, ex=ttl or self.default_ttl)
            await client.set(latest_key, key, ex=ttl or self.default_ttl)
            
            logger.info(f"체크포인트 저장 완료: {key}")
            return key
            
        except Exception as e:
            logger.error(f"체크포인트 저장 실패: {e}")
            raise
    
    def load_checkpoint(self, workflow_id: str, latest: bool = True) -> Optional[CheckpointData]:
        """
        체크포인트 로드 (동기)
        
        Args:
            workflow_id: 워크플로우 ID
            latest: True면 최신 체크포인트, False면 모든 체크포인트 목록
            
        Returns:
            CheckpointData 또는 None
        """
        try:
            client = self.redis_manager.get_sync_client()
            
            if latest:
                # 최신 체크포인트 로드
                latest_key = self._generate_latest_key(workflow_id)
                actual_key = client.get(latest_key)
                
                if not actual_key:
                    logger.warning(f"워크플로우 {workflow_id}의 체크포인트를 찾을 수 없습니다")
                    return None
                
                data = client.get(actual_key)
                if not data:
                    logger.warning(f"체크포인트 데이터를 찾을 수 없습니다: {actual_key}")
                    return None
                
                return CheckpointData.model_validate_json(data)
            else:
                # 모든 체크포인트 목록 - 추후 구현
                raise NotImplementedError("전체 체크포인트 목록 조회는 추후 구현")
                
        except Exception as e:
            logger.error(f"체크포인트 로드 실패: {e}")
            return None
    
    async def load_checkpoint_async(
        self, 
        workflow_id: str, 
        latest: bool = True
    ) -> Optional[CheckpointData]:
        """
        체크포인트 로드 (비동기)
        
        Args:
            workflow_id: 워크플로우 ID
            latest: True면 최신 체크포인트
            
        Returns:
            CheckpointData 또는 None
        """
        try:
            client = await self.redis_manager.get_async_client()
            
            if latest:
                # 최신 체크포인트 로드
                latest_key = self._generate_latest_key(workflow_id)
                actual_key = await client.get(latest_key)
                
                if not actual_key:
                    logger.warning(f"워크플로우 {workflow_id}의 체크포인트를 찾을 수 없습니다")
                    return None
                
                data = await client.get(actual_key)
                if not data:
                    logger.warning(f"체크포인트 데이터를 찾을 수 없습니다: {actual_key}")
                    return None
                
                return CheckpointData.model_validate_json(data)
            else:
                # 모든 체크포인트 목록 - 추후 구현
                raise NotImplementedError("전체 체크포인트 목록 조회는 추후 구현")
                
        except Exception as e:
            logger.error(f"체크포인트 로드 실패: {e}")
            return None
    
    def save_workflow_state(
        self,
        workflow_state: WorkflowState,
        checkpoint_type: str = "periodic"
    ) -> str:
        """
        워크플로우 상태 스냅샷 저장
        
        Args:
            workflow_state: 저장할 워크플로우 상태
            checkpoint_type: 체크포인트 타입
            
        Returns:
            str: 저장된 키
        """
        checkpoint_data = CheckpointData(
            workflow_id=workflow_state.workflow_id,
            checkpoint_type=checkpoint_type,
            state_snapshot=workflow_state
        )
        
        return self.save_checkpoint(checkpoint_data)
    
    async def save_workflow_state_async(
        self,
        workflow_state: WorkflowState,
        checkpoint_type: str = "periodic"
    ) -> str:
        """
        워크플로우 상태 스냅샷 저장 (비동기)
        
        Args:
            workflow_state: 저장할 워크플로우 상태
            checkpoint_type: 체크포인트 타입
            
        Returns:
            str: 저장된 키
        """
        checkpoint_data = CheckpointData(
            workflow_id=workflow_state.workflow_id,
            checkpoint_type=checkpoint_type,
            state_snapshot=workflow_state
        )
        
        return await self.save_checkpoint_async(checkpoint_data)
    
    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회"""
        checkpoint = self.load_checkpoint(workflow_id)
        return checkpoint.state_snapshot if checkpoint else None
    
    async def get_workflow_state_async(self, workflow_id: str) -> Optional[WorkflowState]:
        """워크플로우 상태 조회 (비동기)"""
        checkpoint = await self.load_checkpoint_async(workflow_id)
        return checkpoint.state_snapshot if checkpoint else None
    
    def cleanup_expired_checkpoints(self) -> int:
        """만료된 체크포인트 정리"""
        try:
            client = self.redis_manager.get_sync_client()
            
            # 패턴으로 모든 체크포인트 키 찾기
            pattern = f"{self.key_prefix}:*:*:*"
            keys = client.keys(pattern)
            
            deleted_count = 0
            for key in keys:
                ttl = client.ttl(key)
                if ttl == -1:  # TTL이 설정되지 않은 경우
                    client.expire(key, self.default_ttl)
                elif ttl == -2:  # 키가 존재하지 않는 경우
                    deleted_count += 1
            
            logger.info(f"만료된 체크포인트 {deleted_count}개 정리 완료")
            return deleted_count
            
        except Exception as e:
            logger.error(f"체크포인트 정리 실패: {e}")
            return 0
    
    # =============================================================================
    # API 지원을 위한 확장 메서드들
    # =============================================================================
    
    async def get_checkpoints_by_workflow(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None,
        limit: int = 10
    ) -> List[CheckpointData]:
        """
        특정 워크플로우의 체크포인트 목록 조회
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_type: 체크포인트 타입 필터 (선택)
            limit: 최대 조회 개수
            
        Returns:
            List[CheckpointData]: 체크포인트 목록
        """
        try:
            client = await self.redis_manager.get_async_client()
            
            # 패턴 생성
            if checkpoint_type:
                pattern = f"{self.key_prefix}:{workflow_id}:{checkpoint_type}:*"
            else:
                pattern = f"{self.key_prefix}:{workflow_id}:*:*"
            
            # 키 목록 조회
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            # 타임스탬프로 정렬 (최신순)
            keys.sort(reverse=True)
            
            # 제한 적용
            keys = keys[:limit]
            
            # 데이터 조회
            checkpoints = []
            for key in keys:
                data = await client.get(key)
                if data:
                    try:
                        checkpoint = CheckpointData.model_validate_json(data)
                        checkpoints.append(checkpoint)
                    except Exception as e:
                        logger.warning(f"체크포인트 파싱 실패 ({key}): {e}")
                        continue
            
            logger.info(f"워크플로우 {workflow_id} 체크포인트 {len(checkpoints)}개 조회")
            return checkpoints
            
        except Exception as e:
            logger.error(f"체크포인트 목록 조회 실패: {e}")
            return []
    
    async def get_latest_checkpoint(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None
    ) -> Optional[CheckpointData]:
        """
        최신 체크포인트 조회
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_type: 체크포인트 타입 필터 (선택)
            
        Returns:
            Optional[CheckpointData]: 최신 체크포인트 또는 None
        """
        try:
            checkpoints = await self.get_checkpoints_by_workflow(
                workflow_id, checkpoint_type, limit=1
            )
            return checkpoints[0] if checkpoints else None
            
        except Exception as e:
            logger.error(f"최신 체크포인트 조회 실패: {e}")
            return None
    
    async def delete_checkpoints(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[str] = None
    ) -> int:
        """
        체크포인트 삭제
        
        Args:
            workflow_id: 워크플로우 ID
            checkpoint_type: 체크포인트 타입 필터 (선택)
            
        Returns:
            int: 삭제된 체크포인트 개수
        """
        try:
            client = await self.redis_manager.get_async_client()
            
            # 패턴 생성
            if checkpoint_type:
                pattern = f"{self.key_prefix}:{workflow_id}:{checkpoint_type}:*"
            else:
                pattern = f"{self.key_prefix}:{workflow_id}:*:*"
            
            # 키 목록 조회
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            # 삭제 수행
            deleted_count = 0
            for key in keys:
                result = await client.delete(key)
                if result:
                    deleted_count += 1
            
            # latest 키도 삭제 (전체 워크플로우 삭제 시)
            if not checkpoint_type:
                latest_key = self._generate_latest_key(workflow_id)
                await client.delete(latest_key)
            
            logger.info(f"워크플로우 {workflow_id} 체크포인트 {deleted_count}개 삭제")
            return deleted_count
            
        except Exception as e:
            logger.error(f"체크포인트 삭제 실패: {e}")
            return 0
    
    async def list_all_checkpoints(
        self, 
        page: int = 1, 
        page_size: int = 20,
        checkpoint_type: Optional[str] = None
    ) -> tuple[List[CheckpointData], int]:
        """
        전체 체크포인트 목록 조회 (페이지네이션)
        
        Args:
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지 크기
            checkpoint_type: 체크포인트 타입 필터 (선택)
            
        Returns:
            tuple[List[CheckpointData], int]: (체크포인트 목록, 전체 개수)
        """
        try:
            client = await self.redis_manager.get_async_client()
            
            # 패턴 생성
            if checkpoint_type:
                pattern = f"{self.key_prefix}:*:{checkpoint_type}:*"
            else:
                pattern = f"{self.key_prefix}:*:*:*"
            
            # 키 목록 조회
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            # 타임스탬프로 정렬 (최신순)
            keys.sort(reverse=True)
            
            total = len(keys)
            
            # 페이지네이션 적용
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_keys = keys[start_idx:end_idx]
            
            # 데이터 조회
            checkpoints = []
            for key in page_keys:
                data = await client.get(key)
                if data:
                    try:
                        checkpoint = CheckpointData.model_validate_json(data)
                        checkpoints.append(checkpoint)
                    except Exception as e:
                        logger.warning(f"체크포인트 파싱 실패 ({key}): {e}")
                        continue
            
            logger.info(f"전체 체크포인트 목록 조회: {len(checkpoints)}/{total}")
            return checkpoints, total
            
        except Exception as e:
            logger.error(f"전체 체크포인트 목록 조회 실패: {e}")
            return [], 0
    
    async def health_check(self) -> bool:
        """
        Redis 연결 및 시스템 상태 확인
        
        Returns:
            bool: 시스템 상태 (True: 정상, False: 문제)
        """
        try:
            # 동기 클라이언트 확인
            sync_client = self.redis_manager.get_sync_client()
            sync_result = sync_client.ping()
            
            # 비동기 클라이언트 확인
            async_client = await self.redis_manager.get_async_client()
            async_result = await async_client.ping()
            
            # 테스트 데이터 저장/조회
            test_key = f"{self.key_prefix}:health:test"
            test_data = {"timestamp": datetime.utcnow().isoformat()}
            
            await async_client.set(test_key, json.dumps(test_data), ex=60)
            retrieved_data = await async_client.get(test_key)
            await async_client.delete(test_key)
            
            is_healthy = (
                sync_result and 
                async_result and 
                retrieved_data is not None
            )
            
            logger.info(f"헬스체크 결과: {'정상' if is_healthy else '비정상'}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"헬스체크 실패: {e}")
            return False
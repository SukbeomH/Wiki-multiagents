"""
Feedback Agent (단순화된 버전)

사용자 피드백 수집·정제 루프
- SQLite Store
- 기본 로깅 (Slack 제거)
- Human-in-Loop 시스템
"""

import logging
import json
import sqlite3
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from src.core.schemas.agents import FeedbackIn, FeedbackOut

logger = logging.getLogger(__name__)


class FeedbackItem(BaseModel):
    """피드백 아이템 모델"""
    id: str = Field(..., description="피드백 ID")
    workflow_id: str = Field(..., description="워크플로우 ID")
    user_id: str = Field(..., description="사용자 ID")
    feedback_type: str = Field(..., description="피드백 타입")
    content: str = Field(..., description="피드백 내용")
    rating: Optional[int] = Field(None, description="평점 (1-5)")
    status: str = Field(default="pending", description="처리 상태")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    processed_at: Optional[datetime] = Field(default=None, description="처리 시간")


class FeedbackAgent:
    """단순화된 피드백 처리 에이전트"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Feedback Agent 초기화
        
        Args:
            db_path: SQLite 데이터베이스 경로
        """
        self.db_path = db_path or "data/feedback.db"
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 초기화
        self._init_database()
        
        logger.info(f"Feedback Agent initialized with database: {self.db_path}")
    
    def _init_database(self):
        """SQLite 데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 피드백 테이블 생성
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        rating INTEGER,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        processed_at TEXT
                    )
                """)
                
                # 인덱스 생성
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_id ON feedback(workflow_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON feedback(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON feedback(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON feedback(created_at)")
                
                conn.commit()
                logger.info("Feedback database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize feedback database: {e}")
            raise
    
    def submit_feedback(self, feedback_item: FeedbackItem) -> bool:
        """
        피드백 제출
        
        Args:
            feedback_item: 피드백 아이템
            
        Returns:
            bool: 제출 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO feedback (
                        id, workflow_id, user_id, feedback_type, content, 
                        rating, status, created_at, processed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback_item.id,
                    feedback_item.workflow_id,
                    feedback_item.user_id,
                    feedback_item.feedback_type,
                    feedback_item.content,
                    feedback_item.rating,
                    feedback_item.status,
                    feedback_item.created_at.isoformat(),
                    feedback_item.processed_at.isoformat() if feedback_item.processed_at else None
                ))
                
                conn.commit()
                
                logger.info(f"Feedback submitted successfully: {feedback_item.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False
    
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackItem]:
        """
        피드백 조회
        
        Args:
            feedback_id: 피드백 ID
            
        Returns:
            Optional[FeedbackItem]: 피드백 아이템
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, workflow_id, user_id, feedback_type, content, 
                           rating, status, created_at, processed_at
                    FROM feedback WHERE id = ?
                """, (feedback_id,))
                
                row = cursor.fetchone()
                if row:
                    return FeedbackItem(
                        id=row[0],
                        workflow_id=row[1],
                        user_id=row[2],
                        feedback_type=row[3],
                        content=row[4],
                        rating=row[5],
                        status=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        processed_at=datetime.fromisoformat(row[8]) if row[8] else None
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get feedback {feedback_id}: {e}")
            return None
    
    def list_feedback(
        self, 
        workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[FeedbackItem]:
        """
        피드백 목록 조회
        
        Args:
            workflow_id: 워크플로우 ID 필터
            user_id: 사용자 ID 필터
            status: 상태 필터
            limit: 조회 제한 수
            
        Returns:
            List[FeedbackItem]: 피드백 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, workflow_id, user_id, feedback_type, content, 
                           rating, status, created_at, processed_at
                    FROM feedback WHERE 1=1
                """
                params = []
                
                if workflow_id:
                    query += " AND workflow_id = ?"
                    params.append(workflow_id)
                
                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                feedback_items = []
                for row in cursor.fetchall():
                    feedback_items.append(FeedbackItem(
                        id=row[0],
                        workflow_id=row[1],
                        user_id=row[2],
                        feedback_type=row[3],
                        content=row[4],
                        rating=row[5],
                        status=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        processed_at=datetime.fromisoformat(row[8]) if row[8] else None
                    ))
                
                return feedback_items
                
        except Exception as e:
            logger.error(f"Failed to list feedback: {e}")
            return []
    
    def update_feedback_status(self, feedback_id: str, status: str) -> bool:
        """
        피드백 상태 업데이트
        
        Args:
            feedback_id: 피드백 ID
            status: 새로운 상태
            
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE feedback 
                    SET status = ?, processed_at = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), feedback_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Feedback status updated: {feedback_id} -> {status}")
                    return True
                else:
                    logger.warning(f"Feedback not found: {feedback_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to update feedback status: {e}")
            return False
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """
        피드백 통계 조회
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 전체 피드백 수
                cursor.execute("SELECT COUNT(*) FROM feedback")
                total_feedback = cursor.fetchone()[0]
                
                # 상태별 피드백 수
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM feedback 
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())
                
                # 평점별 피드백 수
                cursor.execute("""
                    SELECT rating, COUNT(*) 
                    FROM feedback 
                    WHERE rating IS NOT NULL
                    GROUP BY rating
                """)
                rating_counts = dict(cursor.fetchall())
                
                # 최근 7일 피드백 수
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM feedback 
                    WHERE created_at >= datetime('now', '-7 days')
                """)
                recent_feedback = cursor.fetchone()[0]
                
                return {
                    "total_feedback": total_feedback,
                    "status_counts": status_counts,
                    "rating_counts": rating_counts,
                    "recent_feedback": recent_feedback,
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {
                "total_feedback": 0,
                "status_counts": {},
                "rating_counts": {},
                "recent_feedback": 0,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    def process(self, input_data: FeedbackIn) -> FeedbackOut:
        """
        Feedback Agent 처리
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            FeedbackOut: 처리 결과
        """
        try:
            # 피드백 아이템 생성
            feedback_item = FeedbackItem(
                id=input_data.feedback_id,
                workflow_id=input_data.workflow_id,
                user_id=input_data.user_id,
                feedback_type=input_data.feedback_type,
                content=input_data.content,
                rating=input_data.rating,
                status="pending"
            )
            
            # 피드백 제출
            submitted = self.submit_feedback(feedback_item)
            
            if submitted:
                # 피드백 처리 (간단한 로직)
                processed = self._process_feedback(feedback_item)
                
                # 상태 업데이트
                new_status = "processed" if processed else "failed"
                self.update_feedback_status(feedback_item.id, new_status)
                
                # 로그 출력
                logger.info(f"Feedback processed: {feedback_item.id} -> {new_status}")
                
                result = FeedbackOut(
                    feedback_id=feedback_item.id,
                    workflow_id=feedback_item.workflow_id,
                    status=new_status,
                    message=f"Feedback {new_status} successfully",
                    processed_at=datetime.now().isoformat(),
                    statistics=self.get_feedback_statistics()
                )
            else:
                result = FeedbackOut(
                    feedback_id=feedback_item.id,
                    workflow_id=feedback_item.workflow_id,
                    status="failed",
                    message="Failed to submit feedback",
                    processed_at=datetime.now().isoformat(),
                    statistics=self.get_feedback_statistics()
                )
            
            logger.info(f"Feedback processing completed: {feedback_item.id}")
            return result
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            
            # 오류 시에도 유효한 결과 반환
            return FeedbackOut(
                feedback_id=input_data.feedback_id,
                workflow_id=input_data.workflow_id,
                status="failed",
                message=f"Processing error: {str(e)}",
                processed_at=datetime.now().isoformat(),
                statistics=self.get_feedback_statistics()
            )
    
    def _process_feedback(self, feedback_item: FeedbackItem) -> bool:
        """
        피드백 처리 로직 (간단한 버전)
        
        Args:
            feedback_item: 처리할 피드백 아이템
            
        Returns:
            bool: 처리 성공 여부
        """
        try:
            # 기본적인 피드백 처리 로직
            logger.info(f"Processing feedback: {feedback_item.id}")
            logger.info(f"Feedback type: {feedback_item.feedback_type}")
            logger.info(f"Content: {feedback_item.content}")
            
            if feedback_item.rating:
                logger.info(f"Rating: {feedback_item.rating}/5")
            
            # 여기에 실제 피드백 처리 로직을 추가할 수 있습니다
            # 예: 감정 분석, 키워드 추출, 우선순위 결정 등
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        에이전트 상태 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            # 데이터베이스 연결 확인
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM feedback")
                total_feedback = cursor.fetchone()[0]
            
            # 통계 정보
            statistics = self.get_feedback_statistics()
            
            health_info = {
                "status": "healthy",
                "agent_type": "feedback",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "database_path": str(self.db_path),
                    "total_feedback": total_feedback
                },
                "statistics": statistics
            }
            
            logger.info("Feedback health check completed")
            return health_info
            
        except Exception as e:
            health_info = {
                "status": "unhealthy",
                "agent_type": "feedback",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            
            logger.error(f"Feedback health check failed: {e}")
            return health_info 
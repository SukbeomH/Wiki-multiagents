"""
Feedback Agent Implementation

피드백 처리를 담당하는 에이전트
- SQLite 저장소
- Slack Webhook
- Human-in-Loop 처리
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import sqlite3
import json
from datetime import datetime
import asyncio
import os

from pydantic import BaseModel, Field

from src.core.schemas.agents import FeedbackIn, FeedbackOut

logger = logging.getLogger(__name__)


class FeedbackItem(BaseModel):
    """피드백 아이템 모델"""
    feedback_id: str = Field(..., description="피드백 ID")
    workflow_id: str = Field(..., description="워크플로우 ID")
    user_id: str = Field(..., description="사용자 ID")
    feedback_type: str = Field(..., description="피드백 타입")
    content: str = Field(..., description="피드백 내용")
    rating: Optional[int] = Field(default=None, description="평점 (1-5)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    status: str = Field(default="pending", description="처리 상태")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    processed_at: Optional[datetime] = Field(default=None, description="처리 시간")


class FeedbackAgent:
    """피드백 처리를 담당하는 에이전트"""
    
    def __init__(self, db_path: Optional[str] = None, slack_webhook_url: Optional[str] = None):
        """
        Feedback Agent 초기화
        
        Args:
            db_path: SQLite 데이터베이스 경로
            slack_webhook_url: Slack Webhook URL
        """
        self.db_path = Path(db_path) if db_path else Path("data/feedback.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.slack_webhook_url = slack_webhook_url
        self._init_database()
        
        logger.info(f"Feedback Agent initialized with db: {self.db_path}")
    
    def _init_database(self) -> None:
        """데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 피드백 테이블 생성
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        feedback_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        feedback_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        rating INTEGER,
                        metadata TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP
                    )
                """)
                
                # 인덱스 생성
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_id ON feedback(workflow_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON feedback(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON feedback(status)")
                
                conn.commit()
                logger.info("Feedback database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def submit_feedback(self, feedback_item: FeedbackItem) -> bool:
        """
        피드백 제출
        
        Args:
            feedback_item: 제출할 피드백 아이템
            
        Returns:
            bool: 제출 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO feedback (
                        feedback_id, workflow_id, user_id, feedback_type,
                        content, rating, metadata, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback_item.feedback_id,
                    feedback_item.workflow_id,
                    feedback_item.user_id,
                    feedback_item.feedback_type,
                    feedback_item.content,
                    feedback_item.rating,
                    json.dumps(feedback_item.metadata),
                    feedback_item.status,
                    feedback_item.created_at.isoformat()
                ))
                
                conn.commit()
                logger.info(f"Feedback submitted: {feedback_item.feedback_id}")
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
                    SELECT feedback_id, workflow_id, user_id, feedback_type,
                           content, rating, metadata, status, created_at, processed_at
                    FROM feedback WHERE feedback_id = ?
                """, (feedback_id,))
                
                row = cursor.fetchone()
                if row:
                    return FeedbackItem(
                        feedback_id=row[0],
                        workflow_id=row[1],
                        user_id=row[2],
                        feedback_type=row[3],
                        content=row[4],
                        rating=row[5],
                        metadata=json.loads(row[6]) if row[6] else {},
                        status=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        processed_at=datetime.fromisoformat(row[9]) if row[9] else None
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get feedback {feedback_id}: {e}")
            return None
    
    def list_feedback(self, workflow_id: Optional[str] = None, 
                     status: Optional[str] = None, 
                     limit: int = 100) -> List[FeedbackItem]:
        """
        피드백 목록 조회
        
        Args:
            workflow_id: 워크플로우 ID 필터
            status: 상태 필터
            limit: 조회 제한 수
            
        Returns:
            List[FeedbackItem]: 피드백 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT feedback_id, workflow_id, user_id, feedback_type,
                           content, rating, metadata, status, created_at, processed_at
                    FROM feedback
                """
                params = []
                
                conditions = []
                if workflow_id:
                    conditions.append("workflow_id = ?")
                    params.append(workflow_id)
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                feedback_items = []
                for row in cursor.fetchall():
                    feedback_items.append(FeedbackItem(
                        feedback_id=row[0],
                        workflow_id=row[1],
                        user_id=row[2],
                        feedback_type=row[3],
                        content=row[4],
                        rating=row[5],
                        metadata=json.loads(row[6]) if row[6] else {},
                        status=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        processed_at=datetime.fromisoformat(row[9]) if row[9] else None
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
                    WHERE feedback_id = ?
                """, (status, datetime.now().isoformat(), feedback_id))
                
                conn.commit()
                logger.info(f"Feedback {feedback_id} status updated to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update feedback status: {e}")
            return False
    
    async def send_slack_notification(self, feedback_item: FeedbackItem) -> bool:
        """
        Slack 알림 전송
        
        Args:
            feedback_item: 피드백 아이템
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            # 실제로는 aiohttp를 사용하여 비동기 HTTP 요청
            message = {
                "text": f"새로운 피드백이 제출되었습니다!",
                "attachments": [
                    {
                        "fields": [
                            {"title": "피드백 ID", "value": feedback_item.feedback_id, "short": True},
                            {"title": "워크플로우 ID", "value": feedback_item.workflow_id, "short": True},
                            {"title": "사용자 ID", "value": feedback_item.user_id, "short": True},
                            {"title": "피드백 타입", "value": feedback_item.feedback_type, "short": True},
                            {"title": "내용", "value": feedback_item.content, "short": False}
                        ]
                    }
                ]
            }
            
            # 여기서는 실제 HTTP 요청 대신 로깅만 수행
            logger.info(f"Slack notification would be sent: {json.dumps(message, ensure_ascii=False)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def process_feedback(self, feedback_id: str) -> Dict[str, Any]:
        """
        피드백 처리
        
        Args:
            feedback_id: 피드백 ID
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        try:
            feedback_item = self.get_feedback(feedback_id)
            if not feedback_item:
                return {"success": False, "error": "Feedback not found"}
            
            # 피드백 타입별 처리 로직
            if feedback_item.feedback_type == "bug_report":
                result = self._process_bug_report(feedback_item)
            elif feedback_item.feedback_type == "feature_request":
                result = self._process_feature_request(feedback_item)
            elif feedback_item.feedback_type == "general":
                result = self._process_general_feedback(feedback_item)
            else:
                result = {"success": False, "error": f"Unknown feedback type: {feedback_item.feedback_type}"}
            
            # 상태 업데이트
            if result.get("success"):
                self.update_feedback_status(feedback_id, "processed")
            else:
                self.update_feedback_status(feedback_id, "failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process feedback {feedback_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _process_bug_report(self, feedback_item: FeedbackItem) -> Dict[str, Any]:
        """버그 리포트 처리"""
        logger.info(f"Processing bug report: {feedback_item.feedback_id}")
        return {
            "success": True,
            "action": "bug_report_processed",
            "priority": "high" if "critical" in feedback_item.content.lower() else "medium"
        }
    
    def _process_feature_request(self, feedback_item: FeedbackItem) -> Dict[str, Any]:
        """기능 요청 처리"""
        logger.info(f"Processing feature request: {feedback_item.feedback_id}")
        return {
            "success": True,
            "action": "feature_request_processed",
            "priority": "medium"
        }
    
    def _process_general_feedback(self, feedback_item: FeedbackItem) -> Dict[str, Any]:
        """일반 피드백 처리"""
        logger.info(f"Processing general feedback: {feedback_item.feedback_id}")
        return {
            "success": True,
            "action": "general_feedback_processed",
            "priority": "low"
        }
    
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
                total_count = cursor.fetchone()[0]
                
                # 상태별 피드백 수
                cursor.execute("SELECT status, COUNT(*) FROM feedback GROUP BY status")
                status_counts = dict(cursor.fetchall())
                
                # 타입별 피드백 수
                cursor.execute("SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type")
                type_counts = dict(cursor.fetchall())
                
                # 평균 평점
                cursor.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL")
                avg_rating = cursor.fetchone()[0]
                
                return {
                    "total_count": total_count,
                    "status_counts": status_counts,
                    "type_counts": type_counts,
                    "average_rating": avg_rating
                }
                
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {}
    
    def process(self, input_data: FeedbackIn) -> FeedbackOut:
        """
        Feedback Agent 메인 처리 함수
        
        Args:
            input_data: FeedbackIn 입력 데이터
            
        Returns:
            FeedbackOut: 피드백 처리 결과
        """
        try:
            logger.info(f"Feedback processing started: {input_data.feedback_id}")
            
            # 피드백 아이템 생성
            feedback_item = FeedbackItem(
                feedback_id=input_data.feedback_id,
                workflow_id=input_data.workflow_id,
                user_id=input_data.user_id,
                feedback_type=input_data.feedback_type,
                content=input_data.content,
                rating=input_data.rating,
                metadata=input_data.metadata
            )
            
            # 피드백 제출
            submit_success = self.submit_feedback(feedback_item)
            if not submit_success:
                raise ValueError("Failed to submit feedback")
            
            # Slack 알림 전송 (필요한 경우)
            slack_sent = False
            if input_data.send_slack_notification and self.slack_webhook_url:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    slack_sent = loop.run_until_complete(
                        self.send_slack_notification(feedback_item)
                    )
                finally:
                    loop.close()
            
            # 피드백 처리
            process_result = self.process_feedback(input_data.feedback_id)
            
            # 결과 반환
            result = FeedbackOut(
                feedback_id=input_data.feedback_id,
                workflow_id=input_data.workflow_id,
                user_id=input_data.user_id,
                feedback_type=input_data.feedback_type,
                content=input_data.content,
                rating=input_data.rating,
                metadata=input_data.metadata,
                status="processed" if process_result.get("success") else "failed",
                submit_success=submit_success,
                slack_sent=slack_sent,
                process_result=process_result,
                success=submit_success and process_result.get("success", False)
            )
            
            logger.info(f"Feedback processing completed: {input_data.feedback_id}")
            return result
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            return FeedbackOut(
                feedback_id=input_data.feedback_id,
                workflow_id=input_data.workflow_id,
                user_id=input_data.user_id,
                feedback_type=input_data.feedback_type,
                content=input_data.content,
                rating=input_data.rating,
                metadata=input_data.metadata,
                status="failed",
                submit_success=False,
                slack_sent=False,
                process_result={"success": False, "error": str(e)},
                success=False,
                error=str(e)
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Feedback Agent 상태 점검
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            # 데이터베이스 확인
            db_exists = self.db_path.exists()
            db_writable = self.db_path.parent.is_dir() and os.access(self.db_path.parent, os.W_OK)
            
            # 통계 정보
            stats = self.get_feedback_statistics()
            
            # Slack Webhook 확인
            slack_configured = bool(self.slack_webhook_url)
            
            return {
                "status": "healthy",
                "db_path": str(self.db_path),
                "db_exists": db_exists,
                "db_writable": db_writable,
                "slack_configured": slack_configured,
                "statistics": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 
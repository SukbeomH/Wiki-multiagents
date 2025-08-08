#!/usr/bin/env python3
"""
피드백 처리 API와 KG 업데이트 통합 E2E 테스트
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.agents.feedback import FeedbackAgent
from src.core.utils.kg_manager import RDFLibKnowledgeGraphManager


class TestFeedbackKGIntegration:
    """피드백 처리 API와 KG 업데이트 통합 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.client = TestClient(app)
        
        # 임시 SQLite 데이터베이스 설정
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 환경 변수 설정
        os.environ['RDFLIB_STORE_URI'] = f'sqlite:///{self.db_path}'
        os.environ['RDFLIB_GRAPH_IDENTIFIER'] = 'test_kg'
    
    def teardown_method(self):
        """테스트 정리"""
        # 임시 파일 삭제
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_feedback_submit_with_kg_updates(self):
        """피드백 제출과 KG 업데이트 통합 테스트"""
        # 테스트 데이터 준비 - 기존 KG에 있는 엔티티 사용
        feedback_data = {
            "workflow_id": f"test_workflow_kg_update_{datetime.now().timestamp()}",
            "user_id": "test_user_456",
            "feedback_type": "entity_correction",
            "content": "사용자 이름이 잘못되었습니다. 'John Doe'로 수정해주세요.",
            "rating": 4,
            "kg_updates": {
                "entities": {
                    "person1": {  # 기존 KG에 있는 엔티티 사용
                        "name": "John Doe",
                        "is_corrected": True,
                        "correction_date": datetime.now().isoformat()
                    }
                }
            }
        }
        
        # API 호출
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        # 응답 검증
        assert response.status_code == 200
        result = response.json()
        
        # 피드백 처리 결과 확인
        assert result["acknowledged"] == True
        assert result["feedback_id"] is not None
        assert result["processing_status"] == "processed"
        
        # KG 업데이트 상태 확인 (실제로는 mock이므로 True로 예상)
        assert "kg_updates_applied" in result
    
    def test_feedback_submit_with_relation_updates(self):
        """관계 업데이트가 포함된 피드백 제출 테스트"""
        feedback_data = {
            "workflow_id": f"test_workflow_relation_update_{datetime.now().timestamp()}",
            "user_id": "test_user_789",
            "feedback_type": "relation_correction",
            "content": "직장 관계가 잘못되었습니다. 회사명을 'Tech Corp'으로 수정해주세요.",
            "kg_updates": {
                "relations": {
                    "person1_WorksFor_company1": {  # 기존 KG에 있는 관계 사용
                        "company_name": "Tech Corp",
                        "is_verified": True,
                        "verification_date": datetime.now().isoformat()
                    }
                }
            }
        }
        
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] == True
    
    def test_feedback_submit_with_relation_endpoint_updates(self):
        """관계 엔드포인트 업데이트가 포함된 피드백 제출 테스트"""
        feedback_data = {
            "workflow_id": f"test_workflow_endpoint_update_{datetime.now().timestamp()}",
            "user_id": "test_user_123",
            "feedback_type": "relationship_change",
            "content": "사용자가 다른 회사로 이직했습니다.",
            "kg_updates": {
                "relation_endpoints": {
                    "person1_WorksFor_company1": {  # 기존 KG에 있는 관계 사용
                        "new_target_id": "company2"  # 기존 KG에 있는 엔티티 사용
                    }
                }
            }
        }
        
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] == True
    
    def test_feedback_submit_without_kg_updates(self):
        """KG 업데이트 없이 피드백 제출 테스트"""
        feedback_data = {
            "workflow_id": f"test_workflow_no_kg_{datetime.now().timestamp()}",
            "user_id": "test_user_999",
            "feedback_type": "general",
            "content": "일반적인 피드백입니다.",
            "rating": 5
        }
        
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] == True
        assert result.get("kg_updates_applied") == False
    
    def test_kg_status_endpoint(self):
        """KG 상태 확인 엔드포인트 테스트"""
        response = self.client.get("/api/v1/feedback/kg/status")
        
        assert response.status_code == 200
        result = response.json()
        
        # KG 상태 정보 확인
        assert "total_entities" in result
        assert "total_relations" in result
        assert "graph_size" in result
        assert "status" in result
        assert result["status"] == "active"
    
    def test_direct_kg_update_endpoint(self):
        """직접 KG 업데이트 엔드포인트 테스트"""
        kg_updates = {
            "entities": {
                "test_entity_001": {
                    "name": "Test Entity",
                    "type": "Person",
                    "created_at": datetime.now().isoformat()
                }
            }
        }
        
        response = self.client.post("/api/v1/feedback/kg/update", json=kg_updates)
        
        assert response.status_code == 200
        result = response.json()
        assert "success" in result
        assert "message" in result
    
    def test_feedback_submit_with_invalid_kg_updates(self):
        """잘못된 KG 업데이트 데이터로 피드백 제출 테스트"""
        feedback_data = {
            "workflow_id": f"test_workflow_invalid_{datetime.now().timestamp()}",
            "user_id": "test_user_invalid",
            "feedback_type": "error_test",
            "content": "잘못된 KG 업데이트 테스트",
            "kg_updates": {
                "entities": {
                    "nonexistent_entity": {
                        "invalid_property": "invalid_value"
                    }
                }
            }
        }
        
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        # 피드백은 성공하지만 KG 업데이트는 실패할 수 있음
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] == True
    
    def test_complex_kg_updates(self):
        """복잡한 KG 업데이트 테스트"""
        feedback_data = {
            "workflow_id": f"test_workflow_complex_{datetime.now().timestamp()}",
            "user_id": "test_user_complex",
            "feedback_type": "complex_correction",
            "content": "여러 엔티티와 관계를 수정해야 합니다.",
            "kg_updates": {
                "entities": {
                    "person1": {  # 기존 KG에 있는 엔티티 사용
                        "name": "Updated Name",
                        "age": 30,
                        "is_verified": True
                    },
                    "company1": {  # 기존 KG에 있는 엔티티 사용
                        "name": "Updated Company",
                        "industry": "Technology"
                    }
                },
                "relations": {
                    "person1_WorksFor_company1": {  # 기존 KG에 있는 관계 사용
                        "position": "Senior Engineer",
                        "start_date": "2023-01-01"
                    }
                },
                "relation_endpoints": {
                    "person1_Knows_person2": {  # 기존 KG에 있는 관계 사용
                        "new_source_id": "person3"  # 기존 KG에 있는 엔티티 사용
                    }
                }
            }
        }
        
        response = self.client.post("/api/v1/feedback/submit", json=feedback_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["acknowledged"] == True


if __name__ == "__main__":
    pytest.main([__file__]) 
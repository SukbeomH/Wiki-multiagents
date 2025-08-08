#!/usr/bin/env python3
"""
RDFLib Knowledge Graph 업데이트 기능 단위 테스트
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

from src.core.utils.kg_manager import RDFLibKnowledgeGraphManager


class TestKGUpdate(unittest.TestCase):
    """Knowledge Graph 업데이트 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 임시 SQLite 데이터베이스 생성
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 환경 변수 설정
        os.environ['RDFLIB_STORE_URI'] = f'sqlite:///{self.db_path}'
        os.environ['RDFLIB_GRAPH_IDENTIFIER'] = 'test_kg'
        os.environ['RDFLIB_NAMESPACE_PREFIX'] = 'http://example.org/kg/'
        
        # KG Manager 초기화
        self.kg_manager = RDFLibKnowledgeGraphManager()
        
        # 테스트 데이터 생성
        self._setup_test_data()
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'kg_manager'):
            self.kg_manager.close()
        
        # 임시 파일 삭제
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _setup_test_data(self):
        """테스트 데이터 설정"""
        # 엔티티 추가
        self.kg_manager.add_entity("person1", "Person", {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com"
        })
        
        self.kg_manager.add_entity("person2", "Person", {
            "name": "Bob",
            "age": 35,
            "email": "bob@example.com"
        })
        
        self.kg_manager.add_entity("company1", "Company", {
            "name": "TechCorp",
            "industry": "Technology"
        })
        
        # 관계 추가
        self.kg_manager.add_relation("person1", "WorksFor", "company1", {
            "start_date": "2020-01-01",
            "position": "Engineer"
        })
        
        self.kg_manager.add_relation("person1", "Knows", "person2", {
            "since": "2019-01-01"
        })
    
    def test_update_entity_success(self):
        """엔티티 업데이트 성공 테스트"""
        # 엔티티 업데이트
        success = self.kg_manager.update_entity("person1", {
            "age": 31,
            "email": "alice.new@example.com",
            "department": "Engineering"
        })
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        entities = self.kg_manager.query_entities("Person", {"name": "Alice"})
        self.assertEqual(len(entities), 1)
        
        entity = entities[0]
        self.assertEqual(entity["properties"]["age"], "31")
        self.assertEqual(entity["properties"]["email"], "alice.new@example.com")
        self.assertEqual(entity["properties"]["department"], "Engineering")
    
    def test_update_entity_not_found(self):
        """존재하지 않는 엔티티 업데이트 테스트"""
        success = self.kg_manager.update_entity("nonexistent", {"name": "New Name"})
        self.assertFalse(success)
    
    def test_update_entity_empty_properties(self):
        """빈 속성으로 엔티티 업데이트 테스트"""
        success = self.kg_manager.update_entity("person1", {})
        self.assertTrue(success)
    
    def test_update_relation_success(self):
        """관계 업데이트 성공 테스트"""
        # 관계 업데이트
        success = self.kg_manager.update_relation("person1_WorksFor_company1", {
            "position": "Senior Engineer",
            "salary": 80000
        })
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        relations = self.kg_manager.query_relations(source_id="person1", target_id="company1")
        self.assertEqual(len(relations), 1)
        
        relation = relations[0]
        self.assertEqual(relation["properties"]["position"], "Senior Engineer")
        self.assertEqual(relation["properties"]["salary"], "80000")
    
    def test_update_relation_not_found(self):
        """존재하지 않는 관계 업데이트 테스트"""
        success = self.kg_manager.update_relation("nonexistent_relation", {"status": "active"})
        self.assertFalse(success)
    
    def test_update_relation_empty_properties(self):
        """빈 속성으로 관계 업데이트 테스트"""
        success = self.kg_manager.update_relation("person1_WorksFor_company1", {})
        self.assertTrue(success)
    
    def test_update_relation_endpoints_success(self):
        """관계 엔드포인트 업데이트 성공 테스트"""
        # 새로운 엔티티 추가
        self.kg_manager.add_entity("person3", "Person", {
            "name": "Charlie",
            "age": 28
        })
        
        # 관계 엔드포인트 업데이트
        success = self.kg_manager.update_relation_endpoints(
            "person1_WorksFor_company1", 
            new_source_id="person3"
        )
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        relations = self.kg_manager.query_relations(source_id="person3", target_id="company1")
        self.assertEqual(len(relations), 1)
        
        # 기존 관계는 더 이상 존재하지 않아야 함
        old_relations = self.kg_manager.query_relations(source_id="person1", target_id="company1")
        self.assertEqual(len(old_relations), 0)
    
    def test_update_relation_endpoints_not_found(self):
        """존재하지 않는 관계 엔드포인트 업데이트 테스트"""
        success = self.kg_manager.update_relation_endpoints(
            "nonexistent_relation", 
            new_source_id="person1"
        )
        self.assertFalse(success)
    
    def test_update_relation_endpoints_empty(self):
        """빈 엔드포인트 업데이트 테스트"""
        success = self.kg_manager.update_relation_endpoints("person1_WorksFor_company1")
        self.assertTrue(success)
    
    def test_update_entity_with_datetime(self):
        """datetime 타입으로 엔티티 업데이트 테스트"""
        test_date = datetime(2023, 1, 1, 12, 0, 0)
        
        success = self.kg_manager.update_entity("person1", {
            "birth_date": test_date,
            "last_login": test_date
        })
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        entities = self.kg_manager.query_entities("Person", {"name": "Alice"})
        self.assertEqual(len(entities), 1)
        
        entity = entities[0]
        self.assertIn("birth_date", entity["properties"])
        self.assertIn("last_login", entity["properties"])
    
    def test_update_entity_with_boolean(self):
        """boolean 타입으로 엔티티 업데이트 테스트"""
        success = self.kg_manager.update_entity("person1", {
            "is_active": True
        })
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        entities = self.kg_manager.query_entities("Person", {"name": "Alice"})
        self.assertEqual(len(entities), 1)
        
        entity = entities[0]
        # boolean 값이 제대로 저장되었는지 확인
        self.assertIn("is_active", entity["properties"])
        # 값이 문자열로 저장되는지 확인
        self.assertTrue(entity["properties"]["is_active"] in ["true", "True", "1"])
    
    def test_update_relation_with_complex_types(self):
        """복잡한 타입으로 관계 업데이트 테스트"""
        test_date = datetime(2023, 1, 1, 12, 0, 0)
        
        success = self.kg_manager.update_relation("person1_WorksFor_company1", {
            "is_active": True,
            "created_at": test_date,
            "priority": 5,
            "description": "Updated relationship"
        })
        
        self.assertTrue(success)
        
        # 업데이트 결과 확인
        relations = self.kg_manager.query_relations(source_id="person1", target_id="company1")
        self.assertEqual(len(relations), 1)
        
        relation = relations[0]
        self.assertEqual(relation["properties"]["is_active"], "true")
        self.assertEqual(relation["properties"]["priority"], "5")
        self.assertEqual(relation["properties"]["description"], "Updated relationship")
    
    def test_sparql_update_query_structure(self):
        """SPARQL UPDATE 쿼리 구조 테스트"""
        # 엔티티 업데이트 전후 그래프 상태 확인
        initial_triples = len(self.kg_manager.graph)
        
        success = self.kg_manager.update_entity("person1", {
            "age": 32,
            "status": "active"
        })
        
        self.assertTrue(success)
        
        # 트리플 수가 적절히 변경되었는지 확인
        final_triples = len(self.kg_manager.graph)
        self.assertGreaterEqual(final_triples, initial_triples)
    
    def test_concurrent_updates(self):
        """동시 업데이트 테스트"""
        # 여러 엔티티 동시 업데이트
        updates = [
            ("person1", {"age": 31}),
            ("person2", {"age": 36}),
            ("company1", {"industry": "Software"})
        ]
        
        for entity_id, properties in updates:
            success = self.kg_manager.update_entity(entity_id, properties)
            self.assertTrue(success)
        
        # 모든 업데이트가 성공적으로 적용되었는지 확인
        person1 = self.kg_manager.query_entities("Person", {"name": "Alice"})
        person2 = self.kg_manager.query_entities("Person", {"name": "Bob"})
        company = self.kg_manager.query_entities("Company", {"name": "TechCorp"})
        
        self.assertEqual(len(person1), 1)
        self.assertEqual(len(person2), 1)
        self.assertEqual(len(company), 1)
        
        self.assertEqual(person1[0]["properties"]["age"], "31")
        self.assertEqual(person2[0]["properties"]["age"], "36")
        self.assertEqual(company[0]["properties"]["industry"], "Software")


if __name__ == '__main__':
    unittest.main() 
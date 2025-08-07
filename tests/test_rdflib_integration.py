#!/usr/bin/env python3
"""
RDFLib 기반 지식 그래프 시스템 통합 테스트
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD
from server.utils.kg_manager import RDFLibKnowledgeGraphManager


class TestRDFLibIntegration(unittest.TestCase):
    """RDFLib 통합 테스트"""
    
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
    
    def tearDown(self):
        """테스트 정리"""
        if hasattr(self, 'kg_manager'):
            self.kg_manager.close()
        
        # 임시 파일 삭제
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_kg_manager_initialization(self):
        """KG Manager 초기화 테스트"""
        self.assertIsNotNone(self.kg_manager)
        self.assertEqual(self.kg_manager.db_path, self.db_path)
        self.assertEqual(self.kg_manager.graph_identifier, 'test_kg')
        self.assertIsNotNone(self.kg_manager.graph)
    
    def test_entity_creation(self):
        """엔티티 생성 테스트"""
        # Person 엔티티 추가
        success = self.kg_manager.add_entity(
            entity_id="person1",
            entity_type="Person",
            properties={
                "name": "Alice Johnson",
                "age": 30,
                "email": "alice@example.com",
                "title": "Software Engineer"
            }
        )
        self.assertTrue(success)
        
        # Company 엔티티 추가
        success = self.kg_manager.add_entity(
            entity_id="company1",
            entity_type="Company",
            properties={
                "name": "TechCorp Inc.",
                "industry": "Technology",
                "founded": 2010
            }
        )
        self.assertTrue(success)
        
        # 엔티티 쿼리 테스트
        entities = self.kg_manager.query_entities(entity_type="Person")
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['id'], "person1")
        self.assertEqual(entities[0]['properties']['name'], "Alice Johnson")
    
    def test_relationship_creation(self):
        """관계 생성 테스트"""
        # 엔티티 먼저 생성
        self.kg_manager.add_entity("person1", "Person", {"name": "Alice"})
        self.kg_manager.add_entity("company1", "Company", {"name": "TechCorp"})
        
        # WorksFor 관계 추가
        success = self.kg_manager.add_relation(
            source_id="person1",
            relation_type="WorksFor",
            target_id="company1",
            properties={"since": "2020-01-15"}
        )
        self.assertTrue(success)
        
        # 관계 쿼리 테스트
        relations = self.kg_manager.query_relations()
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]['source'], "person1")
        self.assertEqual(relations[0]['target'], "company1")
        self.assertEqual(relations[0]['type'], "WorksFor")
    
    def test_sparql_queries(self):
        """SPARQL 쿼리 테스트"""
        # 테스트 데이터 생성
        self.kg_manager.add_entity("person1", "Person", {"name": "Alice", "age": 30})
        self.kg_manager.add_entity("person2", "Person", {"name": "Bob", "age": 35})
        self.kg_manager.add_entity("company1", "Company", {"name": "TechCorp"})
        
        self.kg_manager.add_relation("person1", "WorksFor", "company1")
        self.kg_manager.add_relation("person2", "WorksFor", "company1")
        self.kg_manager.add_relation("person1", "Knows", "person2")
        
        # SPARQL 쿼리 테스트
        query = """
        SELECT ?person ?name ?age
        WHERE {
            ?person a kg:Person .
            ?person kg:name ?name .
            ?person kg:age ?age .
        }
        ORDER BY ?name
        """
        
        results = list(self.kg_manager.graph.query(query))
        self.assertEqual(len(results), 2)
        
        # 이름 순으로 정렬된 결과 확인
        self.assertEqual(str(results[0].name), "Alice")
        self.assertEqual(int(results[0].age), 30)
        self.assertEqual(str(results[1].name), "Bob")
        self.assertEqual(int(results[1].age), 35)
    
    def test_graph_statistics(self):
        """그래프 통계 테스트"""
        # 테스트 데이터 생성
        self.kg_manager.add_entity("person1", "Person", {"name": "Alice"})
        self.kg_manager.add_entity("person2", "Person", {"name": "Bob"})
        self.kg_manager.add_entity("company1", "Company", {"name": "TechCorp"})
        
        self.kg_manager.add_relation("person1", "WorksFor", "company1")
        self.kg_manager.add_relation("person2", "WorksFor", "company1")
        
        # 통계 확인
        stats = self.kg_manager.get_graph_stats()
        self.assertIn('total_triples', stats)
        self.assertIn('entity_count', stats)
        self.assertIn('relation_count', stats)
        self.assertIn('db_path', stats)
        self.assertIn('graph_identifier', stats)
        
        # 예상 값 확인 (엔티티 3개 + 관계 2개 + 타입 정보 등)
        self.assertGreater(stats['total_triples'], 0)
        self.assertGreaterEqual(stats['entity_count'], 3)
        self.assertGreaterEqual(stats['relation_count'], 2)
    
    def test_networkx_export(self):
        """NetworkX 내보내기 테스트"""
        # 테스트 데이터 생성
        self.kg_manager.add_entity("person1", "Person", {"name": "Alice"})
        self.kg_manager.add_entity("company1", "Company", {"name": "TechCorp"})
        self.kg_manager.add_relation("person1", "WorksFor", "company1")
        
        # NetworkX 그래프로 내보내기
        nx_graph = self.kg_manager.export_to_networkx()
        
        if nx_graph:
            # 노드 수 확인 (엔티티 2개)
            self.assertEqual(nx_graph.number_of_nodes(), 2)
            
            # 엣지 수 확인 (관계 1개)
            self.assertEqual(nx_graph.number_of_edges(), 1)
            
            # 노드 속성 확인
            person_node = None
            company_node = None
            
            for node, data in nx_graph.nodes(data=True):
                if data.get('type') == 'Person':
                    person_node = node
                elif data.get('type') == 'Company':
                    company_node = node
            
            self.assertIsNotNone(person_node)
            self.assertIsNotNone(company_node)
            self.assertEqual(nx_graph.nodes[person_node]['name'], 'Alice')
            self.assertEqual(nx_graph.nodes[company_node]['name'], 'TechCorp')
    
    def test_data_persistence(self):
        """데이터 지속성 테스트"""
        # 첫 번째 KG Manager로 데이터 생성
        self.kg_manager.add_entity("person1", "Person", {"name": "Alice"})
        self.kg_manager.add_entity("company1", "Company", {"name": "TechCorp"})
        self.kg_manager.add_relation("person1", "WorksFor", "company1")
        
        # 첫 번째 KG Manager 종료
        self.kg_manager.close()
        
        # 두 번째 KG Manager로 같은 데이터베이스 열기
        kg_manager2 = RDFLibKnowledgeGraphManager()
        
        # 데이터가 유지되는지 확인
        entities = kg_manager2.query_entities()
        self.assertEqual(len(entities), 2)
        
        relations = kg_manager2.query_relations()
        self.assertEqual(len(relations), 1)
        
        kg_manager2.close()
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        # 존재하지 않는 엔티티 삭제 시도
        success = self.kg_manager.delete_entity("nonexistent")
        self.assertFalse(success)
        
        # 존재하지 않는 관계 삭제 시도
        success = self.kg_manager.delete_relation("nonexistent")
        self.assertFalse(success)
        
        # 잘못된 엔티티 타입으로 쿼리
        entities = self.kg_manager.query_entities(entity_type="NonexistentType")
        self.assertEqual(len(entities), 0)


# TestRDFLibMigration 클래스는 마이그레이션 완료로 제거됨


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2) 
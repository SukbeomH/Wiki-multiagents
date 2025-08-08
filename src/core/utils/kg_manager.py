"""
RDFLib 기반 지식 그래프 매니저
Neo4j 대체 구현체 (SQLite 직접 연결 방식)
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import json

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.query import ResultRow

from .config import settings

logger = logging.getLogger(__name__)

class RDFLibKnowledgeGraphManager:
    """
    RDFLib + SQLite 직접 연결 기반 지식 그래프 매니저
    Neo4j 대체 구현체
    """
    
    def __init__(self, db_path: Optional[str] = None, graph_identifier: Optional[str] = None):
        """
        RDFLib 지식 그래프 매니저 초기화
        
        Args:
            db_path: SQLite 데이터베이스 경로 (기본: 환경변수에서 로드)
            graph_identifier: 그래프 식별자 (기본: 환경변수에서 로드)
        """
        # 런타임 환경변수 우선 적용 (테스트에서 setUp 시 주입되는 값 반영)
        env_store_uri = os.getenv('RDFLIB_STORE_URI', settings.RDFLIB_STORE_URI)
        env_graph_id = os.getenv('RDFLIB_GRAPH_IDENTIFIER', settings.RDFLIB_GRAPH_IDENTIFIER)
        env_ns_prefix = os.getenv('RDFLIB_NAMESPACE_PREFIX', settings.RDFLIB_NAMESPACE_PREFIX)

        self.db_path = db_path or self._get_db_path_from_uri(env_store_uri)
        self.graph_identifier = graph_identifier or env_graph_id
        
        # 데이터 디렉토리 생성
        data_dir = Path(self.db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite 연결 초기화
        self._init_sqlite()
        
        # 네임스페이스 설정 (그래프 초기화 전에 설정 필요)
        self.namespace = Namespace(env_ns_prefix)
        
        # RDFLib Graph 초기화 (메모리 기반)
        self.graph = self._initialize_graph()
        
        logger.info(f"RDFLib Knowledge Graph Manager initialized: {self.db_path}")
    
    def _get_db_path_from_uri(self, uri: str) -> str:
        """URI에서 SQLite 파일 경로 추출"""
        if uri.startswith('sqlite:///'):
            return uri.replace('sqlite:///', '')
        return uri
    
    def _init_sqlite(self):
        """SQLite 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # RDF 트리플 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rdf_triples (
                    id INTEGER PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_language TEXT,
                    object_datatype TEXT,
                    graph_identifier TEXT DEFAULT 'kg',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subject ON rdf_triples(subject)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_predicate ON rdf_triples(predicate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_object ON rdf_triples(object)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_graph ON rdf_triples(graph_identifier)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"SQLite database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise
    
    def _initialize_graph(self) -> Graph:
        """
        RDFLib Graph 초기화 (메모리 기반)
        """
        try:
            # 메모리 기반 Graph 생성
            graph = Graph()
            
            # 기존 데이터 로드
            self._load_from_sqlite(graph)
            
            # 초기 스키마 설정
            self._setup_initial_schema(graph)
            
            logger.info(f"Graph initialized with {len(graph)} triples")
            return graph
            
        except Exception as e:
            logger.error(f"Failed to initialize RDFLib graph: {e}")
            raise
    
    def _load_from_sqlite(self, graph: Graph):
        """SQLite에서 트리플 로드"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT subject, predicate, object, object_type, object_language, object_datatype
                FROM rdf_triples 
                WHERE graph_identifier = ?
            ''', (self.graph_identifier,))
            
            for row in cursor.fetchall():
                subject, predicate, obj, obj_type, obj_lang, obj_datatype = row
                
                # RDFLib 객체 생성
                s = URIRef(subject)
                p = URIRef(predicate)
                
                if obj_type == 'Literal':
                    if obj_datatype:
                        o = Literal(obj, datatype=URIRef(obj_datatype))
                    elif obj_lang:
                        o = Literal(obj, lang=obj_lang)
                    else:
                        o = Literal(obj)
                elif obj_type == 'URIRef':
                    o = URIRef(obj)
                elif obj_type == 'BNode':
                    o = BNode(obj)
                else:
                    o = Literal(obj)
                
                graph.add((s, p, o))
            
            conn.close()
            logger.info(f"Loaded {len(graph)} triples from SQLite")
            
        except Exception as e:
            logger.error(f"Failed to load from SQLite: {e}")
    
    def _save_to_sqlite(self):
        """현재 Graph를 SQLite에 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 데이터 삭제 (현재 그래프 식별자)
            cursor.execute('DELETE FROM rdf_triples WHERE graph_identifier = ?', (self.graph_identifier,))
            
            # 새로운 트리플 저장
            for s, p, o in self.graph:
                # 객체 타입 및 메타데이터 추출
                if isinstance(o, Literal):
                    obj_type = 'Literal'
                    obj_lang = o.language if hasattr(o, 'language') else None
                    obj_datatype = str(o.datatype) if o.datatype else None
                elif isinstance(o, URIRef):
                    obj_type = 'URIRef'
                    obj_lang = None
                    obj_datatype = None
                elif isinstance(o, BNode):
                    obj_type = 'BNode'
                    obj_lang = None
                    obj_datatype = None
                else:
                    obj_type = 'Literal'
                    obj_lang = None
                    obj_datatype = None
                
                cursor.execute('''
                    INSERT INTO rdf_triples 
                    (subject, predicate, object, object_type, object_language, object_datatype, graph_identifier)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (str(s), str(p), str(o), obj_type, obj_lang, obj_datatype, self.graph_identifier))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved {len(self.graph)} triples to SQLite")
            
        except Exception as e:
            logger.error(f"Failed to save to SQLite: {e}")
            raise
    
    def _setup_initial_schema(self, graph: Graph):
        """
        초기 RDF 스키마 설정
        """
        # 기본 네임스페이스 바인딩
        graph.bind('rdf', RDF)
        graph.bind('rdfs', RDFS)
        graph.bind('xsd', XSD)
        graph.bind('kg', self.namespace)
        
        # 기본 클래스 정의
        entity_class = self.namespace.Entity
        relation_class = self.namespace.Relation
        
        # 클래스 정의 추가
        graph.add((entity_class, RDF.type, RDFS.Class))
        graph.add((relation_class, RDF.type, RDFS.Class))
        
        logger.info("Initial RDF schema setup completed")
    
    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]) -> bool:
        """
        엔티티 추가
        
        Args:
            entity_id: 엔티티 ID
            entity_type: 엔티티 타입
            properties: 엔티티 속성
            
        Returns:
            bool: 성공 여부
        """
        try:
            entity_uri = self.namespace[entity_id]
            
            # 엔티티 타입 설정
            self.graph.add((entity_uri, RDF.type, self.namespace[entity_type]))
            
            # 속성 추가
            for key, value in properties.items():
                if isinstance(value, str):
                    self.graph.add((entity_uri, self.namespace[key], Literal(value)))
                elif isinstance(value, (int, float)):
                    self.graph.add((entity_uri, self.namespace[key], Literal(value)))
                elif isinstance(value, bool):
                    self.graph.add((entity_uri, self.namespace[key], Literal(value, datatype=XSD.boolean)))
                elif isinstance(value, datetime):
                    self.graph.add((entity_uri, self.namespace[key], Literal(value, datatype=XSD.dateTime)))
            
            # SQLite에 저장
            self._save_to_sqlite()
            
            logger.info(f"Entity added: {entity_id} ({entity_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add entity {entity_id}: {e}")
            return False
    
    def add_relation(self, source_id: str, relation_type: str, target_id: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        관계 추가
        
        Args:
            source_id: 소스 엔티티 ID
            relation_type: 관계 타입
            target_id: 타겟 엔티티 ID
            properties: 관계 속성 (선택적)
            
        Returns:
            bool: 성공 여부
        """
        try:
            source_uri = self.namespace[source_id]
            target_uri = self.namespace[target_id]
            relation_uri = self.namespace[f"{source_id}_{relation_type}_{target_id}"]
            
            # 관계 정의
            self.graph.add((relation_uri, RDF.type, self.namespace[relation_type]))
            self.graph.add((relation_uri, self.namespace.source, source_uri))
            self.graph.add((relation_uri, self.namespace.target, target_uri))
            
            # 관계 속성 추가
            if properties:
                for key, value in properties.items():
                    if isinstance(value, str):
                        self.graph.add((relation_uri, self.namespace[key], Literal(value)))
                    elif isinstance(value, (int, float)):
                        self.graph.add((relation_uri, self.namespace[key], Literal(value)))
                    elif isinstance(value, bool):
                        self.graph.add((relation_uri, self.namespace[key], Literal(value, datatype=XSD.boolean)))
                    elif isinstance(value, datetime):
                        self.graph.add((relation_uri, self.namespace[key], Literal(value, datatype=XSD.dateTime)))
            
            # SQLite에 저장
            self._save_to_sqlite()
            
            logger.info(f"Relation added: {source_id} --{relation_type}--> {target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add relation {source_id} --{relation_type}--> {target_id}: {e}")
            return False
    
    def query_entities(self, entity_type: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        엔티티 쿼리
        
        Args:
            entity_type: 엔티티 타입 필터 (선택적)
            properties: 속성 필터 (선택적)
            
        Returns:
            List[Dict]: 엔티티 목록
        """
        try:
            # SPARQL 쿼리 구성
            query_parts = [
                "SELECT ?entity ?type ?property ?value",
                "WHERE {",
                "  ?entity a ?type .",
                "  FILTER(?type != rdfs:Class)",
                "  FILTER NOT EXISTS { ?entity kg:source ?s }",
                "  FILTER NOT EXISTS { ?entity kg:target ?t }"
            ]
            
            if entity_type:
                query_parts.append(f"  FILTER(?type = kg:{entity_type})")
            
            if properties:
                for key, value in properties.items():
                    if isinstance(value, str):
                        query_parts.append(f"  ?entity kg:{key} \"{value}\" .")
                    else:
                        query_parts.append(f"  ?entity kg:{key} {value} .")
            
            query_parts.extend([
                "  OPTIONAL { ?entity ?property ?value }",
                "}"
            ])
            
            query = " ".join(query_parts)
            results = self.graph.query(query)
            
            # 결과 변환
            entities = {}
            for row in results:
                entity_uri = str(row.entity)
                entity_id = entity_uri.split('/')[-1]
                
                if entity_id not in entities:
                    entities[entity_id] = {
                        'id': entity_id,
                        'type': str(row.type).split('/')[-1],
                        'properties': {}
                    }
                
                if row.property and row.value:
                    prop_name = str(row.property).split('/')[-1]
                    entities[entity_id]['properties'][prop_name] = str(row.value)
            
            return list(entities.values())
            
        except Exception as e:
            logger.error(f"Failed to query entities: {e}")
            return []
    
    def query_relations(self, source_id: Optional[str] = None, target_id: Optional[str] = None, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        관계 쿼리
        
        Args:
            source_id: 소스 엔티티 ID (선택적)
            target_id: 타겟 엔티티 ID (선택적)
            relation_type: 관계 타입 (선택적)
            
        Returns:
            List[Dict]: 관계 목록
        """
        try:
            # SPARQL 쿼리 구성
            query_parts = [
                "SELECT ?relation ?type ?source ?target ?property ?value",
                "WHERE {",
                "  ?relation a ?type .",
                "  ?relation kg:source ?source .",
                "  ?relation kg:target ?target ."
            ]
            
            if relation_type:
                query_parts.append(f"  FILTER(?type = kg:{relation_type})")
            
            if source_id:
                query_parts.append(f"  FILTER(?source = kg:{source_id})")
            
            if target_id:
                query_parts.append(f"  FILTER(?target = kg:{target_id})")
            
            query_parts.extend([
                "  OPTIONAL { ?relation ?property ?value }",
                "}"
            ])
            
            query = " ".join(query_parts)
            results = self.graph.query(query)
            
            # 결과 변환
            relations = {}
            for row in results:
                relation_uri = str(row.relation)
                relation_id = relation_uri.split('/')[-1]
                
                if relation_id not in relations:
                    relations[relation_id] = {
                        'id': relation_id,
                        'type': str(row.type).split('/')[-1],
                        'source': str(row.source).split('/')[-1],
                        'target': str(row.target).split('/')[-1],
                        'properties': {}
                    }
                
                if row.property and row.value:
                    prop_name = str(row.property).split('/')[-1]
                    relations[relation_id]['properties'][prop_name] = str(row.value)
            
            return list(relations.values())
            
        except Exception as e:
            logger.error(f"Failed to query relations: {e}")
            return []
    
    def delete_entity(self, entity_id: str) -> bool:
        """
        엔티티 삭제
        
        Args:
            entity_id: 삭제할 엔티티 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            entity_uri = self.namespace[entity_id]
            
            # 엔티티가 존재하지 않으면 실패 처리
            exists = False
            for _ in self.graph.triples((entity_uri, None, None)):
                exists = True
                break
            if not exists:
                logger.info(f"Entity not found: {entity_id}")
                return False
            
            # 엔티티와 관련된 모든 트리플 삭제
            for s, p, o in self.graph.triples((entity_uri, None, None)):
                self.graph.remove((s, p, o))
            
            for s, p, o in self.graph.triples((None, None, entity_uri)):
                self.graph.remove((s, p, o))
            
            # SQLite에 저장
            self._save_to_sqlite()
            
            logger.info(f"Entity deleted: {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            return False
    
    def delete_relation(self, relation_id: str) -> bool:
        """
        관계 삭제
        
        Args:
            relation_id: 삭제할 관계 ID
            
        Returns:
            bool: 성공 여부
        """
        try:
            relation_uri = self.namespace[relation_id]

            # 존재 여부 확인
            exists = False
            for _ in self.graph.triples((relation_uri, None, None)):
                exists = True
                break
            if not exists:
                logger.info(f"Relation not found: {relation_id}")
                return False

            # 관계와 관련된 모든 트리플 삭제
            for s, p, o in self.graph.triples((relation_uri, None, None)):
                self.graph.remove((s, p, o))
            
            # SQLite에 저장
            self._save_to_sqlite()
            
            logger.info(f"Relation deleted: {relation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete relation {relation_id}: {e}")
            return False
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        그래프 통계 정보 반환
        
        Returns:
            Dict: 그래프 통계
        """
        try:
            # 전체 트리플 수
            total_triples = len(self.graph)
            
            # 엔티티 수
            entity_query = """
            SELECT (COUNT(DISTINCT ?entity) AS ?count)
            WHERE {
                ?entity a ?type .
            }
            """
            entity_count = 0
            for row in self.graph.query(entity_query):
                entity_count = int(row[0])
            
            # 관계 수
            relation_query = """
            SELECT (COUNT(DISTINCT ?relation) AS ?count)
            WHERE {
                ?relation a ?type .
                ?relation kg:source ?source .
                ?relation kg:target ?target .
            }
            """
            relation_count = 0
            for row in self.graph.query(relation_query):
                relation_count = int(row[0])
            
            return {
                'total_triples': total_triples,
                'entity_count': entity_count,
                'relation_count': relation_count,
                'db_path': self.db_path,
                'graph_identifier': self.graph_identifier
            }
            
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {}
    
    def export_to_networkx(self):
        """
        NetworkX 그래프로 변환 (시각화용)
        """
        try:
            import networkx as nx
            
            G = nx.MultiDiGraph()
            
            # 엔티티 추가
            entity_query = """
            SELECT ?entity ?type
            WHERE {
                ?entity a ?type .
            }
            """
            for row in self.graph.query(entity_query):
                entity_id = str(row.entity).split('/')[-1]
                entity_type = str(row.type).split('/')[-1]
                G.add_node(entity_id, type=entity_type)
            
            # 관계 추가
            relation_query = """
            SELECT ?source ?target ?type
            WHERE {
                ?relation a ?type .
                ?relation kg:source ?source .
                ?relation kg:target ?target .
            }
            """
            for row in self.graph.query(relation_query):
                source_id = str(row.source).split('/')[-1]
                target_id = str(row.target).split('/')[-1]
                relation_type = str(row.type).split('/')[-1]
                G.add_edge(source_id, target_id, type=relation_type)
            
            return G
            
        except ImportError:
            logger.warning("NetworkX not available for graph conversion")
            return None
        except Exception as e:
            logger.error(f"Failed to export to NetworkX: {e}")
            return None
    
    def close(self):
        """
        그래프 연결 종료
        """
        try:
            if hasattr(self.graph, 'close'):
                self.graph.close()
            logger.info("RDFLib Knowledge Graph Manager closed")
        except Exception as e:
            logger.error(f"Failed to close graph: {e}")

# 싱글톤 인스턴스
_kg_manager = None

def get_kg_manager() -> RDFLibKnowledgeGraphManager:
    """
    지식 그래프 매니저 싱글톤 인스턴스 반환
    """
    global _kg_manager
    if _kg_manager is None:
        _kg_manager = RDFLibKnowledgeGraphManager()
    return _kg_manager 
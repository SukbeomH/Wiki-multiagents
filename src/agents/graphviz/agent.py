"""
GraphViz Agent Implementation

지식 그래프 시각화를 담당하는 에이전트
- streamlit-agraph 연동
- 그래프 시각화
- 인터랙티브 그래프 생성
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GraphNode(BaseModel):
    """그래프 노드 모델"""
    id: str = Field(..., description="노드 ID")
    label: str = Field(..., description="노드 라벨")
    size: int = Field(default=25, description="노드 크기")
    color: str = Field(default="#1f77b4", description="노드 색상")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="노드 메타데이터")


class GraphEdge(BaseModel):
    """그래프 엣지 모델"""
    source: str = Field(..., description="시작 노드 ID")
    target: str = Field(..., description="도착 노드 ID")
    label: str = Field(default="", description="엣지 라벨")
    color: str = Field(default="#666666", description="엣지 색상")
    width: int = Field(default=1, description="엣지 두께")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="엣지 메타데이터")


class GraphData(BaseModel):
    """그래프 데이터 모델"""
    nodes: List[GraphNode] = Field(default_factory=list, description="노드 목록")
    edges: List[GraphEdge] = Field(default_factory=list, description="엣지 목록")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="그래프 메타데이터")


class GraphVizAgent:
    """지식 그래프 시각화 에이전트"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        GraphViz Agent 초기화
        
        Args:
            output_dir: 그래프 출력 디렉토리
        """
        self.output_dir = Path(output_dir) if output_dir else Path("output/graphs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GraphViz Agent initialized with output dir: {self.output_dir}")
    
    def create_graph_from_triples(self, triples: List[Tuple[str, str, str]]) -> GraphData:
        """
        트리플 데이터로부터 그래프 생성
        
        Args:
            triples: (subject, predicate, object) 형태의 트리플 리스트
            
        Returns:
            GraphData: 생성된 그래프 데이터
        """
        try:
            nodes = []
            edges = []
            node_ids = set()
            
            for subject, predicate, obj in triples:
                # 노드 추가
                if subject not in node_ids:
                    nodes.append(GraphNode(
                        id=subject,
                        label=subject,
                        color=self._get_node_color(subject)
                    ))
                    node_ids.add(subject)
                
                if obj not in node_ids:
                    nodes.append(GraphNode(
                        id=obj,
                        label=obj,
                        color=self._get_node_color(obj)
                    ))
                    node_ids.add(obj)
                
                # 엣지 추가
                edges.append(GraphEdge(
                    source=subject,
                    target=obj,
                    label=predicate,
                    color=self._get_edge_color(predicate)
                ))
            
            graph_data = GraphData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "source": "triples"
                }
            )
            
            logger.info(f"Graph created from {len(triples)} triples: {len(nodes)} nodes, {len(edges)} edges")
            return graph_data
            
        except Exception as e:
            logger.error(f"Failed to create graph from triples: {e}")
            raise
    
    def create_graph_from_entities(self, entities: List[Dict[str, Any]]) -> GraphData:
        """
        엔티티 데이터로부터 그래프 생성
        
        Args:
            entities: 엔티티 정보 딕셔너리 리스트
            
        Returns:
            GraphData: 생성된 그래프 데이터
        """
        try:
            nodes = []
            edges = []
            
            for entity in entities:
                # 엔티티 노드 추가
                nodes.append(GraphNode(
                    id=entity.get("id", entity.get("name", str(len(nodes)))),
                    label=entity.get("name", entity.get("id", "Unknown")),
                    size=entity.get("size", 25),
                    color=entity.get("color", self._get_node_color(entity.get("type", "entity"))),
                    metadata=entity.get("metadata", {})
                ))
                
                # 관계 엣지 추가
                for relation in entity.get("relations", []):
                    if relation.get("target") and relation.get("type"):
                        edges.append(GraphEdge(
                            source=entity.get("id", entity.get("name")),
                            target=relation["target"],
                            label=relation["type"],
                            color=self._get_edge_color(relation["type"])
                        ))
            
            graph_data = GraphData(
                nodes=nodes,
                edges=edges,
                metadata={
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "source": "entities"
                }
            )
            
            logger.info(f"Graph created from {len(entities)} entities: {len(nodes)} nodes, {len(edges)} edges")
            return graph_data
            
        except Exception as e:
            logger.error(f"Failed to create graph from entities: {e}")
            raise
    
    def save_graph_data(self, graph_data: GraphData, filename: str) -> bool:
        """
        그래프 데이터를 JSON 파일로 저장
        
        Args:
            graph_data: 저장할 그래프 데이터
            filename: 출력 파일명
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            output_file = self.output_dir / filename
            
            # Pydantic 모델을 딕셔너리로 변환
            graph_dict = graph_data.model_dump()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(graph_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Graph data saved to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save graph data to {filename}: {e}")
            return False
    
    def load_graph_data(self, filename: str) -> Optional[GraphData]:
        """
        JSON 파일에서 그래프 데이터 로드
        
        Args:
            filename: 로드할 파일명
            
        Returns:
            Optional[GraphData]: 로드된 그래프 데이터
        """
        try:
            input_file = self.output_dir / filename
            
            if not input_file.exists():
                logger.error(f"Graph data file not found: {input_file}")
                return None
            
            with open(input_file, 'r', encoding='utf-8') as f:
                graph_dict = json.load(f)
            
            graph_data = GraphData(**graph_dict)
            logger.info(f"Graph data loaded from: {input_file}")
            return graph_data
            
        except Exception as e:
            logger.error(f"Failed to load graph data from {filename}: {e}")
            return None
    
    def generate_streamlit_graph_config(self, graph_data: GraphData) -> Dict[str, Any]:
        """
        Streamlit agraph 설정 생성
        
        Args:
            graph_data: 그래프 데이터
            
        Returns:
            Dict[str, Any]: Streamlit agraph 설정
        """
        try:
            config = {
                "height": 600,
                "width": 800,
                "directed": True,
                "physics": True,
                "hierarchical": False,
                "node_color": "color",
                "edge_color": "color",
                "node_size": "size",
                "edge_width": "width"
            }
            
            logger.info(f"Streamlit graph config generated for {len(graph_data.nodes)} nodes")
            return config
            
        except Exception as e:
            logger.error(f"Failed to generate streamlit graph config: {e}")
            return {}
    
    def _get_node_color(self, node_type: str) -> str:
        """노드 타입에 따른 색상 반환"""
        color_map = {
            "person": "#ff7f0e",
            "organization": "#2ca02c",
            "location": "#d62728",
            "concept": "#9467bd",
            "event": "#8c564b",
            "entity": "#1f77b4"
        }
        return color_map.get(node_type.lower(), "#1f77b4")
    
    def _get_edge_color(self, relation_type: str) -> str:
        """관계 타입에 따른 색상 반환"""
        color_map = {
            "works_for": "#ff7f0e",
            "located_in": "#2ca02c",
            "part_of": "#d62728",
            "related_to": "#9467bd",
            "similar_to": "#8c564b"
        }
        return color_map.get(relation_type.lower(), "#666666")
    
    def filter_graph_by_node_type(self, graph_data: GraphData, node_types: List[str]) -> GraphData:
        """
        노드 타입으로 그래프 필터링
        
        Args:
            graph_data: 원본 그래프 데이터
            node_types: 포함할 노드 타입 리스트
            
        Returns:
            GraphData: 필터링된 그래프 데이터
        """
        try:
            # 타입별 노드 필터링
            filtered_nodes = [
                node for node in graph_data.nodes
                if any(node_type in node.metadata.get("type", "").lower() 
                      for node_type in node_types)
            ]
            
            # 필터링된 노드와 연결된 엣지만 포함
            filtered_node_ids = {node.id for node in filtered_nodes}
            filtered_edges = [
                edge for edge in graph_data.edges
                if edge.source in filtered_node_ids and edge.target in filtered_node_ids
            ]
            
            filtered_graph = GraphData(
                nodes=filtered_nodes,
                edges=filtered_edges,
                metadata={
                    **graph_data.metadata,
                    "filtered_by": node_types,
                    "original_node_count": len(graph_data.nodes),
                    "original_edge_count": len(graph_data.edges)
                }
            )
            
            logger.info(f"Graph filtered by types {node_types}: {len(filtered_nodes)} nodes, {len(filtered_edges)} edges")
            return filtered_graph
            
        except Exception as e:
            logger.error(f"Failed to filter graph by node types: {e}")
            return graph_data 
"""
GraphViz Agent 테스트
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agents.graphviz import GraphVizAgent, GraphData, GraphNode, GraphEdge


class TestGraphVizAgent:
    """GraphViz Agent 테스트 클래스"""
    
    @pytest.fixture
    def graphviz_agent(self, tmp_path):
        """테스트용 GraphViz Agent 인스턴스"""
        output_dir = tmp_path / "graphs"
        return GraphVizAgent(str(output_dir))
    
    @pytest.fixture
    def sample_triples(self):
        """샘플 트리플 데이터"""
        return [
            ("Alice", "works_for", "TechCorp"),
            ("Bob", "works_for", "TechCorp"),
            ("TechCorp", "located_in", "Seoul"),
            ("Alice", "knows", "Bob")
        ]
    
    @pytest.fixture
    def sample_entities(self):
        """샘플 엔티티 데이터"""
        return [
            {
                "id": "Alice",
                "name": "Alice",
                "type": "person",
                "size": 30,
                "relations": [
                    {"target": "TechCorp", "type": "works_for"},
                    {"target": "Bob", "type": "knows"}
                ]
            },
            {
                "id": "TechCorp",
                "name": "TechCorp",
                "type": "organization",
                "size": 40,
                "relations": [
                    {"target": "Seoul", "type": "located_in"}
                ]
            }
        ]
    
    def test_graphviz_agent_initialization(self, graphviz_agent):
        """GraphViz Agent 초기화 테스트"""
        assert graphviz_agent is not None
        assert hasattr(graphviz_agent, 'output_dir')
        assert graphviz_agent.output_dir.exists()
    
    def test_create_graph_from_triples(self, graphviz_agent, sample_triples):
        """트리플로부터 그래프 생성 테스트"""
        graph_data = graphviz_agent.create_graph_from_triples(sample_triples)
        
        assert isinstance(graph_data, GraphData)
        assert len(graph_data.nodes) == 4  # Alice, Bob, TechCorp, Seoul
        assert len(graph_data.edges) == 4  # 4개의 관계
        
        # 노드 확인
        node_ids = {node.id for node in graph_data.nodes}
        assert "Alice" in node_ids
        assert "Bob" in node_ids
        assert "TechCorp" in node_ids
        assert "Seoul" in node_ids
        
        # 엣지 확인
        edge_labels = {edge.label for edge in graph_data.edges}
        assert "works_for" in edge_labels
        assert "located_in" in edge_labels
        assert "knows" in edge_labels
    
    def test_create_graph_from_entities(self, graphviz_agent, sample_entities):
        """엔티티로부터 그래프 생성 테스트"""
        graph_data = graphviz_agent.create_graph_from_entities(sample_entities)
        
        assert isinstance(graph_data, GraphData)
        assert len(graph_data.nodes) == 2  # Alice, TechCorp
        assert len(graph_data.edges) == 3  # Alice->TechCorp, Alice->Bob, TechCorp->Seoul
        
        # 노드 확인
        node_ids = {node.id for node in graph_data.nodes}
        assert "Alice" in node_ids
        assert "TechCorp" in node_ids
        
        # 노드 크기 확인
        alice_node = next(node for node in graph_data.nodes if node.id == "Alice")
        assert alice_node.size == 30
    
    def test_save_and_load_graph_data(self, graphviz_agent, sample_triples):
        """그래프 데이터 저장 및 로드 테스트"""
        # 그래프 생성
        graph_data = graphviz_agent.create_graph_from_triples(sample_triples)
        
        # 저장
        save_result = graphviz_agent.save_graph_data(graph_data, "test_graph.json")
        assert save_result is True
        
        # 로드
        loaded_data = graphviz_agent.load_graph_data("test_graph.json")
        assert loaded_data is not None
        assert len(loaded_data.nodes) == len(graph_data.nodes)
        assert len(loaded_data.edges) == len(graph_data.edges)
    
    def test_generate_streamlit_graph_config(self, graphviz_agent, sample_triples):
        """Streamlit 그래프 설정 생성 테스트"""
        graph_data = graphviz_agent.create_graph_from_triples(sample_triples)
        config = graphviz_agent.generate_streamlit_graph_config(graph_data)
        
        assert isinstance(config, dict)
        assert "height" in config
        assert "width" in config
        assert "directed" in config
        assert config["height"] == 600
        assert config["width"] == 800
    
    def test_get_node_color(self, graphviz_agent):
        """노드 색상 반환 테스트"""
        assert graphviz_agent._get_node_color("person") == "#ff7f0e"
        assert graphviz_agent._get_node_color("organization") == "#2ca02c"
        assert graphviz_agent._get_node_color("unknown") == "#1f77b4"
    
    def test_get_edge_color(self, graphviz_agent):
        """엣지 색상 반환 테스트"""
        assert graphviz_agent._get_edge_color("works_for") == "#ff7f0e"
        assert graphviz_agent._get_edge_color("located_in") == "#2ca02c"
        assert graphviz_agent._get_edge_color("unknown") == "#666666"
    
    def test_filter_graph_by_node_type(self, graphviz_agent, sample_triples):
        """노드 타입으로 그래프 필터링 테스트"""
        graph_data = graphviz_agent.create_graph_from_triples(sample_triples)
        
        # 노드에 타입 메타데이터 추가
        for node in graph_data.nodes:
            if node.id in ["Alice", "Bob"]:
                node.metadata["type"] = "person"
            elif node.id == "TechCorp":
                node.metadata["type"] = "organization"
            elif node.id == "Seoul":
                node.metadata["type"] = "location"
        
        # person 타입만 필터링
        filtered_graph = graphviz_agent.filter_graph_by_node_type(graph_data, ["person"])
        
        assert len(filtered_graph.nodes) == 2  # Alice, Bob만
        assert len(filtered_graph.edges) == 1  # Alice-knows-Bob만
        assert "person" in filtered_graph.metadata["filtered_by"]
    
    def test_create_graph_from_empty_triples(self, graphviz_agent):
        """빈 트리플로 그래프 생성 테스트"""
        graph_data = graphviz_agent.create_graph_from_triples([])
        
        assert isinstance(graph_data, GraphData)
        assert len(graph_data.nodes) == 0
        assert len(graph_data.edges) == 0
    
    def test_create_graph_from_empty_entities(self, graphviz_agent):
        """빈 엔티티로 그래프 생성 테스트"""
        graph_data = graphviz_agent.create_graph_from_entities([])
        
        assert isinstance(graph_data, GraphData)
        assert len(graph_data.nodes) == 0
        assert len(graph_data.edges) == 0
    
    def test_load_nonexistent_graph_data(self, graphviz_agent):
        """존재하지 않는 파일 로드 테스트"""
        loaded_data = graphviz_agent.load_graph_data("nonexistent.json")
        assert loaded_data is None
    
    def test_save_graph_data_with_invalid_path(self, graphviz_agent, sample_triples):
        """잘못된 경로로 그래프 저장 테스트"""
        graph_data = graphviz_agent.create_graph_from_triples(sample_triples)
        
        # 파일 쓰기 오류 시뮬레이션
        with patch('builtins.open', side_effect=PermissionError):
            save_result = graphviz_agent.save_graph_data(graph_data, "test.json")
            assert save_result is False 
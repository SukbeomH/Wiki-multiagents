"""
Wiki Agent 테스트
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agents.wiki import WikiAgent, WikiContent


class TestWikiAgent:
    """Wiki Agent 테스트 클래스"""
    
    @pytest.fixture
    def wiki_agent(self, tmp_path):
        """테스트용 Wiki Agent 인스턴스"""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # 기본 템플릿 생성
        template_file = template_dir / "wiki_page.md.j2"
        template_file.write_text("# {{ title }}\n\n{{ content }}")
        
        return WikiAgent(str(template_dir))
    
    def test_wiki_agent_initialization(self, wiki_agent):
        """Wiki Agent 초기화 테스트"""
        assert wiki_agent is not None
        assert hasattr(wiki_agent, 'env')
        assert hasattr(wiki_agent, 'template_dir')
    
    def test_create_wiki_page(self, wiki_agent):
        """위키 페이지 생성 테스트"""
        title = "테스트 페이지"
        content = "이것은 테스트 콘텐츠입니다."
        
        wiki_content = wiki_agent.create_wiki_page(
            title=title,
            content=content,
            author="테스트 작성자",
            tags=["test", "wiki"]
        )
        
        assert isinstance(wiki_content, WikiContent)
        assert wiki_content.title == title
        assert content in wiki_content.content
        assert wiki_content.metadata["author"] == "테스트 작성자"
        assert "test" in wiki_content.tags
        assert "wiki" in wiki_content.tags
    
    def test_summarize_content(self, wiki_agent):
        """콘텐츠 요약 테스트"""
        long_content = "첫 번째 문장입니다. " * 50  # 긴 콘텐츠
        max_length = 100
        
        summary = wiki_agent.summarize_content(long_content, max_length)
        
        assert len(summary) <= max_length + 100  # 여유분 포함
        # 요약이 비어있지 않아야 함
        assert len(summary) > 0
        # 요약 정보가 포함되어야 함
        assert "전체" in summary or "요약" in summary
    
    def test_generate_wiki_structure(self, wiki_agent):
        """위키 구조 생성 테스트"""
        topics = [
            "API 엔드포인트",
            "AI 모델",
            "데이터베이스 설정",
            "UI 컴포넌트"
        ]
        
        structure = wiki_agent.generate_wiki_structure(topics)
        
        assert "categories" in structure
        assert "navigation" in structure
        assert "topics" in structure
        assert len(structure["topics"]) == 4
        
        # 카테고리 분류 확인
        assert "API" in structure["categories"]
        assert "AI/ML" in structure["categories"]
        assert "데이터베이스" in structure["categories"]
        assert "사용자 인터페이스" in structure["categories"]
    
    def test_categorize_topic(self, wiki_agent):
        """주제 분류 테스트"""
        assert wiki_agent._categorize_topic("API 엔드포인트") == "API"
        assert wiki_agent._categorize_topic("AI 모델") == "AI/ML"
        assert wiki_agent._categorize_topic("데이터베이스") == "데이터베이스"
        assert wiki_agent._categorize_topic("UI 컴포넌트") == "사용자 인터페이스"
        assert wiki_agent._categorize_topic("기타 주제") == "기타"
    
    def test_save_wiki_content(self, wiki_agent, tmp_path):
        """위키 콘텐츠 저장 테스트"""
        content = WikiContent(
            title="테스트",
            content="# 테스트\n\n내용입니다.",
            metadata={"author": "테스트"},
            tags=["test"]
        )
        
        output_path = tmp_path / "test_wiki.md"
        
        result = wiki_agent.save_wiki_content(content, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        saved_content = output_path.read_text(encoding='utf-8')
        assert "# 테스트" in saved_content
        assert "내용입니다" in saved_content
    
    def test_create_wiki_page_with_template_error(self, wiki_agent):
        """템플릿 오류 처리 테스트"""
        # 존재하지 않는 템플릿 사용
        with patch.object(wiki_agent.env, 'get_template', side_effect=Exception("Template not found")):
            with pytest.raises(Exception):
                wiki_agent.create_wiki_page("제목", "내용")
    
    def test_summarize_content_with_error(self, wiki_agent):
        """요약 오류 처리 테스트"""
        # None 콘텐츠로 테스트
        summary = wiki_agent.summarize_content(None, 100)
        assert summary == "None..."
        
        # 빈 문자열 테스트
        summary = wiki_agent.summarize_content("", 100)
        assert summary == "" 
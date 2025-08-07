"""
Wiki Agent Implementation

위키 작성·요약을 담당하는 에이전트
- Jinja2 템플릿 엔진을 사용한 위키 템플릿 처리
- GPT-4o 스타일러를 활용한 콘텐츠 생성
- Markdown 위키 문서 생성
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WikiContent(BaseModel):
    """위키 콘텐츠 모델"""
    title: str = Field(..., description="위키 문서 제목")
    content: str = Field(..., description="위키 문서 내용 (Markdown)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    tags: List[str] = Field(default_factory=list, description="태그 목록")


class WikiAgent:
    """위키 작성·요약 에이전트"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Wiki Agent 초기화
        
        Args:
            template_dir: Jinja2 템플릿 디렉토리 경로
        """
        self.template_dir = template_dir or str(Path(__file__).parent / "templates")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info(f"Wiki Agent initialized with template dir: {self.template_dir}")
    
    def create_wiki_page(self, title: str, content: str, **kwargs) -> WikiContent:
        """
        위키 페이지 생성
        
        Args:
            title: 페이지 제목
            content: 페이지 내용
            **kwargs: 추가 메타데이터
            
        Returns:
            WikiContent: 생성된 위키 콘텐츠
        """
        try:
            # 기본 템플릿 사용
            template = self.env.get_template("wiki_page.md.j2")
            
            # 메타데이터 준비
            metadata = {
                "created_at": kwargs.get("created_at"),
                "author": kwargs.get("author", "Wiki Agent"),
                "version": kwargs.get("version", "1.0"),
                **kwargs
            }
            
            # 템플릿 렌더링
            rendered_content = template.render(
                title=title,
                content=content,
                metadata=metadata
            )
            
            wiki_content = WikiContent(
                title=title,
                content=rendered_content,
                metadata=metadata,
                tags=kwargs.get("tags", [])
            )
            
            logger.info(f"Wiki page created: {title}")
            return wiki_content
            
        except Exception as e:
            logger.error(f"Failed to create wiki page '{title}': {e}")
            raise
    
    def summarize_content(self, content: str, max_length: int = 500) -> str:
        """
        콘텐츠 요약 생성
        
        Args:
            content: 원본 콘텐츠
            max_length: 최대 요약 길이
            
        Returns:
            str: 요약된 콘텐츠
        """
        try:
            # None이나 빈 문자열 처리
            if content is None:
                return "None..."
            if not content:
                return ""
            
            # 간단한 요약 로직 (실제로는 GPT-4o API 호출)
            lines = content.split('\n')
            summary_lines = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) > max_length:
                    break
                if line.strip():
                    summary_lines.append(line)
                    current_length += len(line) + 1
            
            summary = '\n'.join(summary_lines)
            
            if len(content) > len(summary):
                summary += f"\n\n... (전체 {len(content)}자 중 {len(summary)}자 요약)"
            
            logger.info(f"Content summarized: {len(content)} -> {len(summary)} chars")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize content: {e}")
            if content is None:
                return "None..."
            return content[:max_length] + "..." if len(content) > max_length else content
    
    def generate_wiki_structure(self, topics: List[str]) -> Dict[str, Any]:
        """
        위키 구조 생성
        
        Args:
            topics: 주제 목록
            
        Returns:
            Dict[str, Any]: 위키 구조 정보
        """
        try:
            structure = {
                "main_page": "index",
                "categories": {},
                "navigation": [],
                "topics": topics
            }
            
            # 카테고리별 분류
            for topic in topics:
                category = self._categorize_topic(topic)
                if category not in structure["categories"]:
                    structure["categories"][category] = []
                structure["categories"][category].append(topic)
            
            # 네비게이션 생성
            structure["navigation"] = [
                {"title": "홈", "url": "index"},
                {"title": "카테고리", "url": "categories"},
                {"title": "검색", "url": "search"}
            ]
            
            logger.info(f"Wiki structure generated for {len(topics)} topics")
            return structure
            
        except Exception as e:
            logger.error(f"Failed to generate wiki structure: {e}")
            return {"error": str(e)}
    
    def _categorize_topic(self, topic: str) -> str:
        """주제를 카테고리로 분류"""
        # 간단한 키워드 기반 분류
        topic_lower = topic.lower()
        
        if any(word in topic_lower for word in ["api", "endpoint", "service"]):
            return "API"
        elif any(word in topic_lower for word in ["agent", "ai", "model"]):
            return "AI/ML"
        elif any(word in topic_lower for word in ["database", "db", "storage", "데이터베이스"]):
            return "데이터베이스"
        elif any(word in topic_lower for word in ["ui", "frontend", "interface"]):
            return "사용자 인터페이스"
        else:
            return "기타"
    
    def save_wiki_content(self, content: WikiContent, output_path: str) -> bool:
        """
        위키 콘텐츠를 파일로 저장
        
        Args:
            content: 저장할 위키 콘텐츠
            output_path: 출력 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content.content)
            
            logger.info(f"Wiki content saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save wiki content to {output_path}: {e}")
            return False 
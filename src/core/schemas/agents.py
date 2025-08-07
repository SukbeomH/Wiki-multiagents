"""
에이전트 Input/Output 스키마

PRD Appendix A에 정의된 7개 에이전트의 Input/Output JSON 스키마를 
Pydantic 모델로 구현
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Research Agent - 키워드 기반 문서 수집·캐싱
# =============================================================================

class ResearchIn(BaseModel):
    """Research Agent 입력 스키마"""
    keyword: str = Field(
        description="검색할 키워드",
        min_length=1,
        max_length=200
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="수집할 문서 수 (1-50)"
    )
    search_engines: List[str] = Field(
        default=["duckduckgo", "wikipedia"],
        description="사용할 검색 엔진 목록"
    )
    cache_enabled: bool = Field(
        default=True,
        description="캐시 사용 여부"
    )
    language: str = Field(
        default="ko",
        description="검색 언어 (ko, en, etc.)"
    )

    @field_validator('search_engines')
    @classmethod
    def validate_search_engines(cls, v: List[str]) -> List[str]:
        """검색 엔진 목록 검증"""
        allowed_engines = {"duckduckgo", "wikipedia", "google", "bing"}
        for engine in v:
            if engine not in allowed_engines:
                raise ValueError(f"지원하지 않는 검색 엔진: {engine}. 지원 엔진: {allowed_engines}")
        return v

    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """언어 코드 검증"""
        allowed_languages = {"ko", "en", "ja", "zh", "es", "fr", "de", "it", "pt", "ru"}
        if v not in allowed_languages:
            raise ValueError(f"지원하지 않는 언어 코드: {v}. 지원 언어: {allowed_languages}")
        return v


class ResearchOut(BaseModel):
    """Research Agent 출력 스키마"""
    docs: List[str] = Field(
        description="수집된 문서 내용 리스트",
        min_length=0
    )
    metadata: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="각 문서의 메타데이터 (URL, 제목, 소스 등)"
    )
    cache_hit: bool = Field(
        default=False,
        description="캐시에서 가져왔는지 여부"
    )
    processing_time: float = Field(
        default=0.0,
        ge=0.0,
        description="처리 시간 (초)"
    )

    @field_validator('docs')
    @classmethod
    def validate_docs(cls, v: List[str]) -> List[str]:
        """문서 내용 검증"""
        for i, doc in enumerate(v):
            if not doc.strip():
                raise ValueError(f"문서 {i+1}이 빈 문자열입니다.")
        return v

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """메타데이터 구조 검증"""
        for i, meta in enumerate(v):
            if not isinstance(meta, dict):
                raise ValueError(f"메타데이터 {i+1}이 딕셔너리가 아닙니다.")
            
            # 오류 메타데이터인 경우 다른 검증 규칙 적용
            if 'error' in meta:
                # 오류 메타데이터는 error, error_type, search_engine, region 키를 가져야 함
                error_keys = {"error", "error_type", "search_engine", "region"}
                missing_keys = error_keys - set(meta.keys())
                if missing_keys:
                    raise ValueError(f"오류 메타데이터 {i+1}에 필수 키가 누락되었습니다: {missing_keys}")
            else:
                # 일반 메타데이터는 title, url, source 키를 가져야 함
                required_keys = {"title", "url", "source"}
                missing_keys = required_keys - set(meta.keys())
                if missing_keys:
                    raise ValueError(f"메타데이터 {i+1}에 필수 키가 누락되었습니다: {missing_keys}")
        return v

    @field_validator('processing_time')
    @classmethod
    def validate_processing_time(cls, v: float) -> float:
        """처리 시간 검증"""
        if v < 0:
            raise ValueError("처리 시간은 음수일 수 없습니다.")
        return v


# =============================================================================
# Extractor Agent - 엔티티·관계 추출·증분 업데이트  
# =============================================================================

class Entity(BaseModel):
    """추출된 엔티티"""
    id: str = Field(description="엔티티 고유 식별자")
    type: str = Field(description="엔티티 타입 (PERSON, ORGANIZATION, CONCEPT 등)")
    name: str = Field(description="엔티티 이름")
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="추가 속성 정보"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="추출 확신도 (0.0-1.0)"
    )


class Relation(BaseModel):
    """추출된 관계"""
    source: str = Field(description="출발 엔티티 ID")
    target: str = Field(description="도착 엔티티 ID") 
    predicate: str = Field(description="관계 타입 (RELATED_TO, PART_OF 등)")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="관계 확신도 (0.0-1.0)"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="관계의 추가 속성"
    )


class ExtractorIn(BaseModel):
    """Extractor Agent 입력 스키마"""
    docs: List[str] = Field(
        description="추출할 문서 리스트",
        min_length=1
    )
    extraction_mode: str = Field(
        default="comprehensive",
        description="추출 모드 (comprehensive, fast, focused)"
    )
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="추출할 엔티티 타입 제한 (None시 모든 타입)"
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="최소 확신도 임계값"
    )


class ExtractorOut(BaseModel):
    """Extractor Agent 출력 스키마"""
    entities: List[Entity] = Field(
        description="추출된 엔티티 리스트"
    )
    relations: List[Relation] = Field(
        description="추출된 관계 리스트"
    )
    processing_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="처리 통계 (문서 수, 토큰 수, 처리 시간 등)"
    )


# =============================================================================
# Retriever Agent - 유사 문서 선별·문맥 보강 (RAG)
# =============================================================================

class RetrieverIn(BaseModel):
    """Retriever Agent 입력 스키마"""
    query: str = Field(
        description="검색 쿼리",
        min_length=1
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="반환할 문서 수"
    )
    similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="유사도 임계값"
    )
    include_metadata: bool = Field(
        default=True,
        description="메타데이터 포함 여부"
    )


class RetrieverOut(BaseModel):
    """Retriever Agent 출력 스키마"""
    doc_ids: List[str] = Field(
        description="검색된 문서 ID 리스트"
    )
    context: str = Field(
        description="결합된 컨텍스트 텍스트"
    )
    similarities: List[float] = Field(
        default_factory=list,
        description="각 문서의 유사도 점수"
    )
    metadata: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="각 문서의 메타데이터"
    )


# =============================================================================
# Wiki Agent - Markdown 위키 작성·요약
# =============================================================================

class WikiIn(BaseModel):
    """Wiki Agent 입력 스키마"""
    node_id: str = Field(
        description="위키를 생성할 노드 ID"
    )
    context_docs: List[str] = Field(
        default_factory=list,
        description="참고할 컨텍스트 문서들"
    )
    style: str = Field(
        default="comprehensive",
        description="위키 스타일 (comprehensive, summary, technical)"
    )
    include_references: bool = Field(
        default=True,
        description="참고 문헌 포함 여부"
    )
    max_length: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="최대 길이 (단어 수)"
    )


class WikiOut(BaseModel):
    """Wiki Agent 출력 스키마"""
    markdown: str = Field(
        description="생성된 Markdown 위키 내용"
    )
    summary: str = Field(
        description="위키 요약"
    )
    references: List[Dict[str, str]] = Field(
        default_factory=list,
        description="참고 문헌 리스트"
    )
    word_count: int = Field(
        default=0,
        description="생성된 위키의 단어 수"
    )


# =============================================================================  
# GraphViz Agent - 지식 그래프 시각화
# =============================================================================

class GraphVizIn(BaseModel):
    """GraphViz Agent 입력 스키마"""
    kg_diff: Dict[str, Any] = Field(
        description="지식 그래프 변경사항"
    )
    layout_type: str = Field(
        default="force_directed",
        description="레이아웃 타입 (force_directed, hierarchical, circular)"
    )
    node_limit: int = Field(
        default=100,
        ge=10,
        le=500,
        description="표시할 노드 수 제한"
    )
    include_labels: bool = Field(
        default=True,
        description="노드 라벨 표시 여부"
    )
    color_scheme: str = Field(
        default="category",
        description="색상 스킴 (category, centrality, cluster)"
    )


class GraphVizOut(BaseModel):
    """GraphViz Agent 출력 스키마"""
    graph_json: Dict[str, Any] = Field(
        description="streamlit-agraph 호환 그래프 JSON"
    )
    layout_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="레이아웃 설정"
    )
    stats: Dict[str, int] = Field(
        default_factory=dict,
        description="그래프 통계 (노드 수, 엣지 수 등)"
    )


# =============================================================================
# Supervisor Agent - 오케스트레이션·Lock·Retry
# =============================================================================

class SupervisorIn(BaseModel):
    """Supervisor Agent 입력 스키마"""
    trace_id: str = Field(
        description="워크플로우 추적 ID"
    )
    user_id: str = Field(
        description="사용자 ID"
    )
    request: Dict[str, Any] = Field(
        description="요청 데이터"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="작업 우선순위 (1=최고, 10=최저)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="최대 재시도 횟수"
    )


class SupervisorOut(BaseModel):
    """Supervisor Agent 출력 스키마"""
    status: str = Field(
        description="워크플로우 상태 (success, failed, in_progress)"
    )
    result: Dict[str, Any] = Field(
        description="실행 결과 데이터"
    )
    execution_time: float = Field(
        default=0.0,
        description="총 실행 시간 (초)"
    )
    retry_count: int = Field(
        default=0,
        description="재시도 횟수"
    )
    error_details: Optional[str] = Field(
        default=None,
        description="오류 발생 시 상세 정보"
    )


# =============================================================================
# Feedback Agent - 사용자 피드백 수집·정제 루프
# =============================================================================

class FeedbackIn(BaseModel):
    """Feedback Agent 입력 스키마"""
    node_id: str = Field(
        description="피드백 대상 노드 ID"
    )
    feedback: str = Field(
        description="사용자 피드백 내용",
        min_length=1,
        max_length=5000
    )
    feedback_type: str = Field(
        default="correction",
        description="피드백 타입 (correction, addition, deletion, suggestion)"
    )
    user_id: str = Field(
        description="피드백 제공자 ID"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="피드백 확신도"
    )


class FeedbackOut(BaseModel):
    """Feedback Agent 출력 스키마"""
    acknowledged: bool = Field(
        description="피드백 접수 여부"
    )
    feedback_id: str = Field(
        description="피드백 고유 ID"
    )
    processing_status: str = Field(
        default="queued",
        description="처리 상태 (queued, processing, applied, rejected)"
    )
    estimated_impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="예상 영향도 분석"
    )
    requires_human_review: bool = Field(
        default=False,
        description="사람의 검토가 필요한지 여부"
    )


# =============================================================================
# 검증 및 유틸리티
# =============================================================================

def validate_agent_schemas():
    """모든 에이전트 스키마의 기본 검증"""
    try:
        # 각 스키마 인스턴스 생성 테스트
        research_in = ResearchIn(keyword="test")
        research_out = ResearchOut(docs=["test doc"])
        
        extractor_in = ExtractorIn(docs=["test"])
        entity = Entity(id="1", type="CONCEPT", name="Test")
        relation = Relation(source="1", target="2", predicate="RELATED_TO", confidence=0.9)
        extractor_out = ExtractorOut(entities=[entity], relations=[relation])
        
        retriever_in = RetrieverIn(query="test query")
        retriever_out = RetrieverOut(doc_ids=["1"], context="test context")
        
        wiki_in = WikiIn(node_id="1")
        wiki_out = WikiOut(markdown="# Test", summary="Test summary")
        
        graphviz_in = GraphVizIn(kg_diff={})
        graphviz_out = GraphVizOut(graph_json={})
        
        supervisor_in = SupervisorIn(trace_id="1", user_id="1", request={})
        supervisor_out = SupervisorOut(status="success", result={})
        
        feedback_in = FeedbackIn(node_id="1", feedback="test", user_id="1")
        feedback_out = FeedbackOut(acknowledged=True, feedback_id="1")
        
        return True
    except Exception as e:
        print(f"스키마 검증 실패: {e}")
        return False


if __name__ == "__main__":
    # 스키마 검증 실행
    if validate_agent_schemas():
        print("✅ 모든 에이전트 스키마가 정상적으로 정의되었습니다!")
    else:
        print("❌ 스키마 검증 실패")
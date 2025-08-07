import pytest
from pydantic import ValidationError

from server.schemas.agents import ResearchIn, ResearchOut


@pytest.mark.schemas
class TestResearchInSchema:
    def test_valid_research_in(self):
        obj = ResearchIn(keyword="test", search_engines=["duckduckgo"], language="ko", top_k=10)
        assert obj.keyword == "test"
        assert obj.top_k == 10
        assert obj.language == "ko"

    def test_invalid_search_engine(self):
        with pytest.raises(ValidationError):
            ResearchIn(keyword="test", search_engines=["invalid"], language="ko")

    def test_invalid_language(self):
        with pytest.raises(ValidationError):
            ResearchIn(keyword="test", language="xx")

    def test_keyword_min_length(self):
        with pytest.raises(ValidationError):
            ResearchIn(keyword="", language="ko")

    @pytest.mark.parametrize("top_k", [0, 51])
    def test_top_k_bounds_invalid(self, top_k):
        with pytest.raises(ValidationError):
            ResearchIn(keyword="test", language="ko", top_k=top_k)

    @pytest.mark.parametrize("top_k", [1, 50])
    def test_top_k_bounds_valid(self, top_k):
        obj = ResearchIn(keyword="test", language="ko", top_k=top_k)
        assert obj.top_k == top_k


@pytest.mark.schemas
class TestResearchOutSchema:
    def test_valid_research_out(self):
        obj = ResearchOut(
            docs=["doc1", "doc2"],
            metadata=[{"title": "t1", "url": "http://a", "source": "duckduckgo"}],
            processing_time=0.01,
            cache_hit=False,
        )
        assert len(obj.docs) == 2

    def test_docs_cannot_have_empty_string(self):
        with pytest.raises(ValidationError):
            ResearchOut(docs=["ok", " "])

    def test_metadata_requires_keys(self):
        with pytest.raises(ValidationError):
            ResearchOut(docs=["ok"], metadata=[{"title": "t1"}])

    def test_error_metadata_shape(self):
        # 오류 메타데이터는 별도의 키 세트를 허용
        obj = ResearchOut(
            docs=[],
            metadata=[{
                "error": "failed",
                "error_type": "Exception",
                "search_engine": "duckduckgo",
                "region": "wt-wt",
            }],
            processing_time=0.0,
            cache_hit=False,
        )
        assert obj.cache_hit is False

    def test_processing_time_ge_zero(self):
        with pytest.raises(ValidationError):
            ResearchOut(docs=["ok"], processing_time=-0.1)

"""
Retriever Agent API 라우터
쿼리 임베딩 생성 및 유사도 검색 엔드포인트 제공
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.core.schemas.agents import RetrieverIn, RetrieverOut
from src.agents.retriever import get_retriever_agent, RetrieverAgent

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/retriever",
    tags=["retriever"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/search",
    response_model=RetrieverOut,
    summary="벡터 유사도 검색",
    description="쿼리 텍스트를 임베딩으로 변환하고 FAISS에서 유사한 문서를 검색합니다."
)
async def search_documents(
    input_data: RetrieverIn,
    agent: RetrieverAgent = Depends(get_retriever_agent)
):
    """
    벡터 유사도 검색 수행
    
    Args:
        input_data: 검색 쿼리 및 옵션
        agent: Retriever Agent 인스턴스
        
    Returns:
        RetrieverOut: 검색 결과 (문서 ID, 컨텍스트, 유사도 점수)
        
    Raises:
        HTTPException: 검색 실패 시
    """
    try:
        logger.info(f"벡터 검색 요청: {input_data.query[:100]}...")
        
        # Retriever Agent를 통한 검색 수행
        result = agent.process(input_data)
        
        logger.info(f"검색 완료: {len(result.doc_ids)}개 문서 반환")
        return result
        
    except ValueError as e:
        logger.error(f"검색 처리 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"검색 처리 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail="내부 서버 오류가 발생했습니다."
        )


@router.post(
    "/embed",
    summary="텍스트 임베딩 생성",
    description="텍스트를 4096차원 임베딩 벡터로 변환합니다."
)
async def create_embedding(
    query: str,
    agent: RetrieverAgent = Depends(get_retriever_agent)
):
    """
    텍스트 임베딩 생성
    
    Args:
        query: 임베딩할 텍스트
        agent: Retriever Agent 인스턴스
        
    Returns:
        Dict: 임베딩 벡터와 메타데이터
        
    Raises:
        HTTPException: 임베딩 생성 실패 시
    """
    try:
        logger.info(f"임베딩 생성 요청: {query[:100]}...")
        
        # 임베딩 벡터 생성
        embedding_vector = agent.create_query_embedding(query)
        
        return {
            "embedding": embedding_vector.tolist(),
            "dimension": embedding_vector.shape[0],
            "model": "text-embedding-3-large",
            "query": query
        }
        
    except ValueError as e:
        logger.error(f"임베딩 생성 오류: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"임베딩 생성 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail="내부 서버 오류가 발생했습니다."
        )


@router.get(
    "/health",
    summary="Retriever Agent 상태 점검",
    description="Retriever Agent와 관련 서비스들의 상태를 확인합니다."
)
async def health_check(
    agent: RetrieverAgent = Depends(get_retriever_agent)
):
    """
    Retriever Agent 상태 점검
    
    Args:
        agent: Retriever Agent 인스턴스
        
    Returns:
        Dict: 상태 정보
    """
    try:
        health_info = agent.health_check()
        
        # 상태에 따른 HTTP 코드 결정
        status_code = 200 if health_info["status"] == "healthy" else 503
        
        return JSONResponse(
            content=health_info,
            status_code=status_code
        )
        
    except Exception as e:
        logger.error(f"상태 점검 오류: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e)
            },
            status_code=503
        )


@router.get(
    "/stats",
    summary="벡터 스토어 통계",
    description="FAISS 벡터 스토어의 상태와 통계 정보를 반환합니다."
)
async def get_vector_store_stats(
    agent: RetrieverAgent = Depends(get_retriever_agent)
):
    """
    벡터 스토어 통계 정보 조회
    
    Args:
        agent: Retriever Agent 인스턴스
        
    Returns:
        Dict: 벡터 스토어 통계
    """
    try:
        stats = agent.vector_store.get_stats()
        
        return {
            "vector_store": stats,
            "embedding_model": "text-embedding-3-large",
            "dimension": 4096,
            "timestamp": logger.name  # 현재 시간 대신 로거 이름 사용
        }
        
    except Exception as e:
        logger.error(f"통계 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 실패: {str(e)}"
        )
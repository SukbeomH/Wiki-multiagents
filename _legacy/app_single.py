# ==============================================================================
# 1. 라이브러리 임포트 (Imports & Setup)
# ==============================================================================
# 최신 LangChain v0.2.x 및 v0.3.x 버전에 맞춰 모듈화된 라이브러리들을 임포트합니다.
import os
import logging
import json
import glob
import time
import streamlit as st
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, BaseMessage

# LangGraph 및 에이전트 관련
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages # AnyMessageEditor 대신 add_messages를 임포트
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool


# Azure OpenAI 및 RAG 관련
# langchain-azure-openai -> langchain_openai 로 변경
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader # PDF 로더 변경
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from ddgs import DDGS # ddgs 라이브러리로 변경


# ==============================================================================
# 2. 환경설정 및 모델 팩토리 (Configuration & Model Factory)
# ==============================================================================
AZURE_API_VERSION = "2024-02-01"
DATA_DIR = "data" # 업로드된 PDF를 저장할 디렉토리
APP_GRAPH_VERSION = "3"

# ==============================================================================
# 로깅 설정 (Terminal 로그 출력)
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("econ-analyzer")
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
try:
    logger.setLevel(_log_level)
except Exception:
    logger.setLevel(logging.INFO)

def setup_environment():
    """환경 변수를 로드하고 필수 변수가 설정되었는지 확인합니다."""
    load_dotenv()
    logger.info("[env] .env 로드 완료, 필수 환경변수 검증 시작")
    required_vars = ["AOAI_ENDPOINT", "AOAI_API_KEY", "AOAI_DEPLOY_GPT4O", "AOAI_DEPLOY_EMBED_3_LARGE"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error("[env] 필수 환경변수 누락: %s", var)
            raise ValueError(f"환경 변수 '{var}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    logger.info("[env] 필수 환경변수 검증 완료")

class AzureModelFactory:
    """Azure OpenAI 모델 인스턴스를 중앙에서 관리하고 생성하는 헬퍼 클래스."""
    def __init__(self):
        self.endpoint = os.getenv("AOAI_ENDPOINT")
        self.api_key = os.getenv("AOAI_API_KEY")
        self.gpt4o_deployment = os.getenv("AOAI_DEPLOY_GPT4O")
        self.embedding_deployment = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")

    def get_chat_model(self, temperature=0):
        """채팅 모델 인스턴스를 반환합니다."""
        logger.info("[model] AzureChatOpenAI 인스턴스 생성 (temp=%s)", temperature)
        return AzureChatOpenAI(
            azure_deployment=self.gpt4o_deployment,
            api_version=AZURE_API_VERSION,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            temperature=temperature,
            max_retries=5,  # 재시도 횟수 증가 (3 → 5)
            timeout=60,     # 타임아웃 증가 (30 → 60초)
            request_timeout=60,  # 요청 타임아웃 명시적 설정
        )

    def get_embedding_model(self):
        """임베딩 모델 인스턴스를 반환합니다."""
        logger.info("[model] AzureOpenAIEmbeddings 인스턴스 생성")
        return AzureOpenAIEmbeddings(
            azure_deployment=self.embedding_deployment,
            api_version=AZURE_API_VERSION,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )

# ==============================================================================
# 2.5. ddgs 기반 웹 검색 도구 정의 (New Web Search Tool)
# ==============================================================================
def web_search_func(query: str, max_results: int = 5) -> str:
    """
    ddgs 라이브러리를 사용하여 DuckDuckGo 웹 검색을 수행하고 결과를 포맷팅합니다.
    재시도 로직과 폴백 메커니즘을 포함합니다.
    """
    # 웹검색 토글 확인
    if not st.session_state.get("web_search_enabled", True):
        return "웹검색이 비활성화되어 있습니다. 사이드바에서 웹검색을 활성화하세요."
    
    max_retries = 3
    retry_delay = 1  # 초기 재시도 지연 (초)
    
    for attempt in range(max_retries):
        try:
            logger.info("[web-search] query='%s' (시도 %d/%d)", query, attempt + 1, max_retries)
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=max_results)]
                if not results:
                    logger.info("[web-search] 결과 0건")
                    return "검색 결과가 없습니다."
                
                formatted_results = []
                for i, res in enumerate(results, 1):
                    formatted_results.append(f"결과 {i}: {res['title']}\n요약: {res['body']}\nURL: {res['href']}\n---")
                logger.info("[web-search] 결과 %d건", len(formatted_results))
                return "\n".join(formatted_results)
                
        except Exception as e:
            logger.warning("[web-search] 시도 %d/%d 실패: %s", attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프
            else:
                logger.exception("[web-search] 모든 시도 실패")
                return f"웹 검색 중 오류가 발생했습니다: {e}"
    
    return "웹 검색을 완료할 수 없습니다."


# ==============================================================================
# 3. 고급 RAG 파이프라인 구축 (Advanced RAG Pipeline with Dynamic PDF Loading)
# ==============================================================================
def save_faiss_index(vectorstore, index_path: str):
    """FAISS 인덱스를 파일로 저장합니다."""
    try:
        vectorstore.save_local(index_path)
        logger.info("[rag] FAISS 인덱스 저장 완료: %s", index_path)
        return True
    except Exception as e:
        logger.exception("[rag] FAISS 인덱스 저장 실패: %s", e)
        return False

def load_faiss_index(index_path: str, embeddings):
    """저장된 FAISS 인덱스를 로드합니다."""
    try:
        if os.path.exists(index_path):
            # allow_dangerous_deserialization=True 추가 (로컬에서 생성한 파일이므로 안전)
            vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            logger.info("[rag] FAISS 인덱스 로드 완료: %s", index_path)
            return vectorstore
        else:
            logger.warning("[rag] FAISS 인덱스 파일이 존재하지 않음: %s", index_path)
            return None
    except Exception as e:
        logger.exception("[rag] FAISS 인덱스 로드 실패: %s", e)
        return None

def create_mmr_retriever(vectorstore, k=5, fetch_k=20, lambda_mult=0.7):
    """MMR (Maximum Marginal Relevance) 검색을 사용하는 리트리버를 생성합니다."""
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": lambda_mult  # 다양성 vs 관련성 균형 (0.7 = 관련성 70%, 다양성 30%)
        }
    )

def create_similarity_retriever(vectorstore, k=5, score_threshold=0.7):
    """유사도 기반 검색을 사용하는 리트리버를 생성합니다."""
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k,
            "score_threshold": score_threshold
        }
    )

def create_compressed_retriever(base_retriever, llm):
    """컨텍스트 압축을 사용하는 리트리버를 생성합니다."""
    try:
        compressor = LLMChainExtractor.from_llm(llm)
        compressed_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever
        )
        logger.info("[rag] ContextualCompressionRetriever 생성 완료")
        return compressed_retriever
    except Exception as e:
        logger.warning("[rag] ContextualCompressionRetriever 생성 실패, 기본 리트리버 사용: %s", e)
        return base_retriever

@st.cache_resource
def build_rag_pipeline(cache_key: str):
    """
    'data' 폴더 내의 모든 PDF를 동적으로 로드하여 RAG 파이프라인을 구축합니다.
    FAISS 인덱스 영속화, MMR 검색, 컨텍스트 압축을 포함합니다.
    """
    logger.info("[rag] 파이프라인 빌드 시작 (cache_key=%s)", cache_key)
    
    # FAISS 인덱스 저장 경로
    index_path = os.path.join(DATA_DIR, "faiss_index")
    
    # 임베딩 모델 초기화
    from langchain_openai import AzureOpenAIEmbeddings
    endpoint = os.getenv("AOAI_ENDPOINT")
    api_key = os.getenv("AOAI_API_KEY")
    embed_deploy = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=embed_deploy,
        api_version=AZURE_API_VERSION,
        azure_endpoint=endpoint,
        api_key=api_key,
    )
    
    # PDF 파일 변경 확인
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    current_pdf_mtime = max([os.path.getmtime(f) for f in pdf_files]) if pdf_files else 0
    
    # 인덱스 무효화 파일 확인
    invalidation_file = os.path.join(index_path, "invalidation.txt")
    index_needs_rebuild = True
    
    if os.path.exists(invalidation_file):
        try:
            with open(invalidation_file, 'r') as f:
                stored_mtime = float(f.read().strip())
            if stored_mtime >= current_pdf_mtime:
                index_needs_rebuild = False
                logger.info("[rag] PDF 파일 변경 없음, 기존 인덱스 사용 가능")
        except Exception as e:
            logger.warning("[rag] 무효화 파일 읽기 실패: %s", e)
    
    # 저장된 인덱스 로드 시도
    vectorstore = None
    if not index_needs_rebuild:
        vectorstore = load_faiss_index(index_path, embeddings)
    
    if vectorstore is None:
        # 새로 빌드
        logger.info("[rag] 새 인덱스 빌드 시작")
        all_docs = []
        
        pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
        logger.info("[rag] PDF 파일 수: %d", len(pdf_files))
        
        if not pdf_files:
            st.sidebar.warning("참고 자료가 없습니다. 기본 데이터로 분석합니다.")
            from langchain_core.documents import Document
            all_docs = [Document(page_content="[문서 1: 2025년 8월 통화정책방향 결정문 (가상)]\n- 제목: 한국은행 금융통화위원회, 기준금리 현 3.50%로 동결 결정\n- 결정 배경: 소비자물가 상승률이 2%대 후반으로 둔화되었으나, 여전히 높은 수준의 가계부채와 부동산 PF 부실 위험 등 금융안정 리스크가 상존하고 있음을 고려.")]
        else:
            for pdf_path in pdf_files:
                try:
                    loader = PyMuPDFLoader(pdf_path)
                    all_docs.extend(loader.load())
                    logger.info("[rag] 로드 완료: %s", os.path.basename(pdf_path))
                except Exception as e:
                    logger.exception("[rag] 로드 실패: %s", os.path.basename(pdf_path))
                    st.sidebar.error(f"'{os.path.basename(pdf_path)}' 파일 로드 실패: {e}")

        if not all_docs:
            logger.error("[rag] 문서 로드 실패: all_docs=0")
            raise ValueError("RAG를 위한 문서를 로드할 수 없습니다.")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_docs = text_splitter.split_documents(all_docs)
        logger.info("[rag] 텍스트 분할 완료: chunks=%d", len(split_docs))

        vectorstore = FAISS.from_documents(documents=split_docs, embedding=embeddings)
        logger.info("[rag] FAISS 벡터스토어 생성 완료")
        
        # 인덱스 저장
        if save_faiss_index(vectorstore, index_path):
            # 무효화 파일 저장
            try:
                os.makedirs(index_path, exist_ok=True)
                with open(invalidation_file, 'w') as f:
                    f.write(str(current_pdf_mtime))
                logger.info("[rag] 무효화 파일 저장 완료: %s", current_pdf_mtime)
            except Exception as e:
                logger.warning("[rag] 무효화 파일 저장 실패: %s", e)
    else:
        logger.info("[rag] 기존 FAISS 인덱스 사용")

    # LLM 초기화
    from langchain_openai import AzureChatOpenAI
    chat_deploy = os.getenv("AOAI_DEPLOY_GPT4O")
    llm = AzureChatOpenAI(
        azure_deployment=chat_deploy,
        api_version=AZURE_API_VERSION,
        azure_endpoint=endpoint,
        api_key=api_key,
        temperature=0,
        max_retries=5,
        timeout=60,
        request_timeout=60,
    )
    
    # 검색 전략 선택 (환경 변수 또는 기본값)
    search_strategy = os.getenv("RAG_SEARCH_STRATEGY", "mmr").lower()
    
    if search_strategy == "mmr":
        # MMR 리트리버 생성 (다양성과 관련성 균형)
        base_retriever = create_mmr_retriever(
            vectorstore, 
            k=int(os.getenv("RAG_K", "5")), 
            fetch_k=int(os.getenv("RAG_FETCH_K", "20")),
            lambda_mult=float(os.getenv("RAG_LAMBDA_MULT", "0.7"))
        )
        logger.info("[rag] MMR 리트리버 생성 완료 (k=%s, fetch_k=%s, lambda=%s)", 
                   os.getenv("RAG_K", "5"), os.getenv("RAG_FETCH_K", "20"), os.getenv("RAG_LAMBDA_MULT", "0.7"))
    elif search_strategy == "similarity":
        # 유사도 기반 리트리버 생성
        base_retriever = create_similarity_retriever(
            vectorstore,
            k=int(os.getenv("RAG_K", "5")),
            score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.7"))
        )
        logger.info("[rag] 유사도 리트리버 생성 완료 (k=%s, threshold=%s)", 
                   os.getenv("RAG_K", "5"), os.getenv("RAG_SCORE_THRESHOLD", "0.7"))
    else:
        # 기본 리트리버
        base_retriever = vectorstore.as_retriever(
            search_kwargs={"k": int(os.getenv("RAG_K", "5"))}
        )
        logger.info("[rag] 기본 리트리버 생성 완료 (k=%s)", os.getenv("RAG_K", "5"))
    
    # 컨텍스트 압축 리트리버 생성 (선택적)
    use_compression = os.getenv("RAG_USE_COMPRESSION", "false").lower() == "true"
    if use_compression:
        try:
            compressed_retriever = create_compressed_retriever(base_retriever, llm)
            logger.info("[rag] 컨텍스트 압축 리트리버 생성 완료")
            final_retriever = compressed_retriever
        except Exception as e:
            logger.warning("[rag] 컨텍스트 압축 실패, 기본 리트리버 사용: %s", e)
            final_retriever = base_retriever
    else:
        logger.info("[rag] 컨텍스트 압축 비활성화")
        final_retriever = base_retriever
    
    # MultiQueryRetriever로 최종 래핑
    retriever = MultiQueryRetriever.from_llm(retriever=final_retriever, llm=llm)
    logger.info("[rag] MultiQueryRetriever 초기화 완료")
    
    return retriever

# ==============================================================================
# 4. 멀티 에이전트 정의 (Multi-Agent Definition)
# ==============================================================================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

class _SimpleAgentExecutor:
    """도구 없이 최종 응답만 생성하는 간단 실행기.
    AgentExecutor와 인터페이스를 맞춰 {"output": str} 형태를 반환합니다.
    """
    def __init__(self, runnable):
        self._runnable = runnable

    def invoke(self, inputs):
        text = self._runnable.invoke(inputs)
        return {"output": text}




def create_agent(llm: AzureChatOpenAI, tools: list, system_prompt: str, use_react: bool = True):
    tools_desc = "\n".join([f"- {t.name}: {getattr(t, 'description', '')}" for t in tools])
    tool_names = ", ".join([t.name for t in tools])
    logger.info("[agent] 에이전트 생성: tools=[%s], mode=%s", tool_names, "react" if use_react else "final")

    if use_react and len(tools) > 0:
        # 최신 LangChain 방식: create_tool_calling_agent 사용
        from langchain.agents import create_tool_calling_agent
        
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "{system_prompt}\n\n사용 가능한 도구:\n{tools}\n\n도구 이름 목록: {tool_names}"
            ),
            ("human", "{input}"),
            # 최신 방식: agent_scratchpad는 자동으로 처리됨
            ("placeholder", "{agent_scratchpad}"),
        ]).partial(system_prompt=system_prompt, tools=tools_desc, tool_names=tool_names)
        
        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)

    # 도구가 없거나(use_react=False) 최종 응답만 원하는 경우: 일반 LLM 체인
    from langchain_core.output_parsers import StrOutputParser
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}\n\n요청에 대해 최종 답변만 생성하세요. 불필요한 사고과정이나 도구 호출 지시문을 출력하지 마세요. 항상 구체적인 결론을 포함한 한국어 최종 답변을 간결히 작성하세요."),
        ("human", "{input}")
    ]).partial(system_prompt=system_prompt)
    runnable = prompt | llm | StrOutputParser()
    return _SimpleAgentExecutor(runnable)

def agent_node(state, agent, name):
    """에이전트 노드 실행 함수 - 타임아웃과 재시도 로직 포함"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            last_message = state["messages"][-1]
            # 1) Supervisor 라우팅 지시문은 입력으로 쓰지 않되, 실행은 진행(최근 Human 입력 사용)
            #    → 라우팅 지시문 때문에 완전히 스킵되어 응답이 비는 문제를 방지
            if isinstance(getattr(last_message, "content", ""), str):
                content_upper = last_message.content.strip().upper()
                if content_upper.startswith("ROUTE:") or content_upper.startswith("FINAL ANSWER:"):
                    logger.info("[agent-node:%s] 라우팅 지시문 감지 → 최근 Human 입력으로 강제 실행", name)
                    # 그대로 진행하여 아래 direct invoke 분기로 이어집니다.
            
            # Supervisor에서 생성된 tool call들을 모두 처리하여 ToolMessage로 응답
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                logger.info("[agent-node:%s] tool_calls=%d", name, len(last_message.tool_calls))
                responses = []
                for tool_call in last_message.tool_calls:
                    # 현재 노드 이름과 일치하는 툴콜만 처리 (다른 노드용 툴콜은 건너뜀)
                    tool_name = (tool_call.get('name') or '').lower()
                    if name not in tool_name:
                        continue
                    tool_args = tool_call.get('args', {})
                    # {'input': '...'} 또는 {'__arg1': '...'} 형태 대응
                    if isinstance(tool_args, dict):
                        worker_input = tool_args.get('input') or tool_args.get('query')
                        if worker_input is None and len(tool_args) > 0:
                            worker_input = next(iter(tool_args.values()))
                    else:
                        worker_input = tool_args
                    logger.info("[agent-node:%s] invoke input len=%d", name, len((worker_input or "")))
                    # 입력이 문자열이 아닐 수 있으므로 문자열로 안전 변환
                    if not isinstance(worker_input, str):
                        try:
                            worker_input = json.dumps(worker_input, ensure_ascii=False)
                        except Exception:
                            worker_input = str(worker_input)
                    # AgentExecutor 호출 - agent_scratchpad는 자동으로 처리됨
                    invoke_result = agent.invoke({
                        "input": worker_input or ""
                    })
                    result_text = invoke_result.get("output", "")
                    responses.append(ToolMessage(content=result_text, tool_call_id=tool_call.get('id')))
                return {"messages": responses}
            
            # 툴콜이 없는 경우에도 해당 노드에서 직접 작업 실행 (ReAct 없이 단순 체인)
            worker_input = ""
            for msg in reversed(state.get("messages", [])):
                if isinstance(msg, HumanMessage):
                    worker_input = getattr(msg, "content", "")
                    break
            logger.info("[agent-node:%s] direct invoke (no tool_calls), input len=%d", name, len(worker_input or ""))
            
            # 2) 에이전트 타입에 따라 호출 분기
            if isinstance(agent, AgentExecutor):
                # agent_scratchpad 제거 - 최신 LangChain에서는 자동으로 처리됨
                invoke_result = agent.invoke({
                    "input": worker_input or ""
                })
                result_text = invoke_result.get("output", "")
                logger.info("[agent-node:%s] result len=%d (agent)", name, len(result_text or ""))
            else:
                # _SimpleAgentExecutor 등 일반 체인: invoke가 dict 반환하도록 래핑됨
                result_text = agent.invoke({"input": worker_input or ""}).get("output", "")
                logger.info("[agent-node:%s] result len=%d (chain)", name, len(result_text or ""))
            
            # 근거 품질 평가 및 재조회 로직 (Researcher 노드에서만)
            if name == "researcher":
                # 출처 정보 추출
                sources = []
                lines = result_text.split('\n')
                in_source_section = False
                
                for line in lines:
                    if '[출처 정보]' in line:
                        in_source_section = True
                        continue
                    elif in_source_section and line.strip().startswith('['):
                        break
                    elif in_source_section and line.strip():
                        source_info = extract_source_info(line)
                        sources.append(source_info)
                
                # 근거 품질 평가
                quality_scores = evaluate_evidence_quality(result_text, sources)
                
                # 근거 부족 시 재조회 트리거
                if quality_scores["quality_score"] < 6 or len(sources) < 2:
                    logger.warning("[agent-node:researcher] 근거 부족 감지 (품질=%d, 출처=%d), 재조회 트리거", 
                                 quality_scores["quality_score"], len(sources))
                    
                    # 재조회를 위한 추가 검색 요청
                    enhanced_result = result_text + "\n\n[추가 검색 필요]\n근거가 부족하여 추가 정보 수집이 필요합니다."
                    return {"messages": [HumanMessage(content=enhanced_result, name=name)]}
                
                logger.info("[agent-node:researcher] 근거 품질 평가 완료 (품질=%d, 출처=%d)", 
                           quality_scores["quality_score"], len(sources))
            
            return {"messages": [HumanMessage(content=result_text, name=name)]}
            
        except Exception as e:
            logger.warning("[agent-node:%s] 시도 %d/%d 실패: %s", name, attempt + 1, max_retries, e)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프
            else:
                logger.exception("[agent-node:%s] 모든 시도 실패", name)
                error_message = f"Error in {name} Agent: {e}"
                return {"messages": [HumanMessage(content=error_message, name="error")]}
    
    # 모든 재시도 실패 시
    error_message = f"Error in {name} Agent: 모든 재시도 실패"
    return {"messages": [HumanMessage(content=error_message, name="error")]}

# 최대 반복 횟수 및 타임아웃 설정
MAX_ITERATIONS = 10
TIMEOUT_SECONDS = 300

# 출처 및 인용 관련 설정
CITATION_FORMAT = """
출처: [{source_name}] {page_info}
근거: {evidence_text}
신뢰도: {confidence_score}
"""

RESEARCHER_OUTPUT_FORMAT = """
[수집된 정보]
{content}

[출처 정보]
{source_citations}

[신뢰도 평가]
- 정보 품질: {quality_score}/10
- 출처 신뢰성: {reliability_score}/10
- 최신성: {recency_score}/10
"""

ANALYST_OUTPUT_FORMAT = """
[분석 결과]
{analysis}

[근거 및 출처]
{citations}

[결론]
{conclusion}
"""

def extract_source_info(content: str) -> dict:
    """텍스트에서 출처 정보를 추출합니다."""
    import re  # 함수 시작 부분에서 임포트
    
    source_info = {
        "source_name": "알 수 없음",
        "page_info": "",
        "evidence_text": content[:200] + "..." if len(content) > 200 else content,
        "confidence_score": "중간"
    }
    
    # PDF 파일명 추출 시도
    if "PDF" in content or ".pdf" in content.lower():
        pdf_match = re.search(r'([^/\\]+\.pdf)', content, re.IGNORECASE)
        if pdf_match:
            source_info["source_name"] = pdf_match.group(1)
    
    # 페이지 정보 추출 시도
    page_match = re.search(r'페이지\s*(\d+)', content)
    if page_match:
        source_info["page_info"] = f"페이지 {page_match.group(1)}"
    
    # URL 추출 시도
    url_match = re.search(r'https?://[^\s]+', content)
    if url_match:
        source_info["source_name"] = url_match.group(0)
        source_info["page_info"] = "웹 페이지"
    
    return source_info

def format_citations(sources: list) -> str:
    """출처 목록을 포맷팅된 인용 문자열로 변환합니다."""
    if not sources:
        return "출처 정보 없음"
    
    citations = []
    for i, source in enumerate(sources, 1):
        citation = CITATION_FORMAT.format(
            source_name=source.get("source_name", "알 수 없음"),
            page_info=source.get("page_info", ""),
            evidence_text=source.get("evidence_text", "")[:150] + "..." if len(source.get("evidence_text", "")) > 150 else source.get("evidence_text", ""),
            confidence_score=source.get("confidence_score", "중간")
        )
        citations.append(f"{i}. {citation.strip()}")
    
    return "\n".join(citations)

def evaluate_evidence_quality(content: str, sources: list) -> dict:
    """근거의 품질을 평가합니다."""
    quality_score = 5  # 기본값
    reliability_score = 5
    recency_score = 5
    
    # 출처 수에 따른 품질 점수 조정
    if len(sources) >= 3:
        quality_score += 2
    elif len(sources) >= 1:
        quality_score += 1
    
    # 내용 길이에 따른 품질 점수 조정
    if len(content) > 500:
        quality_score += 1
    
    # 출처 신뢰성 평가
    for source in sources:
        source_name = source.get("source_name", "").lower()
        if "한국은행" in source_name or "bok" in source_name:
            reliability_score += 2
        elif "gov" in source_name or "정부" in source_name:
            reliability_score += 1
    
    # 점수 범위 제한
    quality_score = min(10, max(1, quality_score))
    reliability_score = min(10, max(1, reliability_score))
    recency_score = min(10, max(1, recency_score))
    
    return {
        "quality_score": quality_score,
        "reliability_score": reliability_score,
        "recency_score": recency_score
    }

def extract_preview_sources(content: str) -> list:
    """응답 내용에서 근거 정보를 추출하여 미리보기용으로 반환합니다."""
    import re
    
    sources = []
    
    # 출처 정보 섹션 찾기
    source_patterns = [
        r'출처:\s*\[([^\]]+)\]\s*([^\n]+)',
        r'근거:\s*([^\n]+)',
        r'\[근거 및 출처\](.*?)(?=\n\[|\n$|$)',
        r'출처 정보\](.*?)(?=\n\[|\n$|$)'
    ]
    
    for pattern in source_patterns:
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                source_text = ' '.join(match).strip()
            else:
                source_text = match.strip()
            
            if source_text and len(source_text) > 10:
                # 텍스트 정리
                source_text = re.sub(r'\s+', ' ', source_text)
                source_text = source_text[:100] + "..." if len(source_text) > 100 else source_text
                sources.append(source_text)
    
    # 중복 제거 및 상위 3개 반환
    unique_sources = list(dict.fromkeys(sources))  # 순서 유지하면서 중복 제거
    return unique_sources[:3]

def create_supervisor(llm: AzureChatOpenAI, agent_names: List[str]):
    system_prompt = (
        "당신은 여러 AI 에이전트를 관리하는 감독관입니다. 당신의 유일한 임무는 라우팅 결정입니다.\n\n"
        "**엄격한 출력 규칙:**\n"
        "당신은 반드시 다음 중 하나만 정확히 출력해야 합니다:\n"
        "1. ROUTE: researcher  (정보 수집 필요)\n"
        "2. ROUTE: analyst     (분석 필요)\n"
        "3. ROUTE: END         (작업 완료)\n\n"
        "**금지사항:**\n"
        "- 'Final Answer:' 사용 금지 (Analyst가 담당)\n"
        "- 설명, 생각, JSON, 도구호출 금지\n"
        "- 규칙 외 모든 출력 금지\n\n"
        "**라우팅 기준:**\n"
        "- 정보 부족 시: ROUTE: researcher\n"
        "- 분석 필요 시: ROUTE: analyst\n"
        "- 완료 시: ROUTE: END\n"
        "- 불명확 시: ROUTE: END (안전한 종료)\n\n"
        "**반복 한도:**\n"
        "- 최대 10회 반복 후 자동 종료\n"
        "- 무한 루프 방지를 위해 보수적 라우팅\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        MessagesPlaceholder("messages"),
    ]).partial(system_prompt=system_prompt)

    def supervisor_node(state):
        messages = state.get("messages", []) if isinstance(state, dict) else []
        logger.info("[supervisor] 입력 메시지 수=%d", len(messages))
        
        # 반복 한도 체크
        if len(messages) > MAX_ITERATIONS:
            logger.warning("[supervisor] 최대 반복 횟수 도달 (%d), 강제 종료", MAX_ITERATIONS)
            return {"messages": [HumanMessage(content="ROUTE: END", name="supervisor")]}
        
        # 타임아웃 체크 (간단한 구현)
        current_time = time.time()
        if hasattr(supervisor_node, '_start_time'):
            if current_time - supervisor_node._start_time > TIMEOUT_SECONDS:
                logger.warning("[supervisor] 타임아웃 도달 (%d초), 강제 종료", TIMEOUT_SECONDS)
                return {"messages": [HumanMessage(content="ROUTE: END", name="supervisor")]}
        else:
            supervisor_node._start_time = current_time
        
        formatted = prompt.invoke({"messages": messages})
        ai_msg = llm.invoke(formatted)
        return {"messages": [ai_msg]}

    return supervisor_node


# ==============================================================================
# 5. LangGraph 그래프 구성 (Graph Construction)
# ==============================================================================
def create_graph(llm, retriever):
    researcher_tools = [
        Tool(name="bok_document_search", func=retriever.invoke, description="사용자가 업로드한 PDF 문서나 한국은행 공식 문서를 검색하여 특정 경제 용어, 정책, 보고서 내용을 찾습니다."),
        Tool(name="web_search", func=web_search_func, description="최신 경제 뉴스나 실시간 시장 반응 등 현재 정보를 위해 웹을 검색합니다.")
    ]
    researcher_system_prompt = """당신은 전문 경제 연구원입니다. 사용자의 요청에 따라 제공된 문서와 웹에서 정확하고 객관적인 정보를 찾아서 제공하는 역할을 합니다.

**출처 정보 포함 필수:**
- 모든 정보는 반드시 출처를 명시해야 합니다
- PDF 문서: 파일명과 페이지 번호 포함
- 웹 검색: URL과 사이트명 포함
- 한국은행 공식 문서: 문서명과 발행일 포함

**출력 형식:**
[수집된 정보]
- 구체적이고 객관적인 정보 내용

[출처 정보]
1. 출처: [파일명/URL] 페이지/사이트 정보
   근거: 관련 텍스트 요약
   신뢰도: 높음/중간/낮음

[신뢰도 평가]
- 정보 품질: X/10
- 출처 신뢰성: X/10  
- 최신성: X/10

**근거 부족 시:**
- 더 많은 정보를 수집하기 위해 추가 검색을 수행하세요
- 다양한 출처에서 정보를 수집하여 신뢰성을 높이세요"""

    researcher_agent = create_agent(
        llm,
        researcher_tools,
        researcher_system_prompt,
        use_react=True,
    )
    analyst_system_prompt = """당신은 날카로운 통찰력을 가진 경제 분석가입니다. 주어진 데이터(context)를 바탕으로 사용자의 질문에 대한 깊이 있는 분석과 명확한 답변을 생성합니다.

**분석 요구사항:**
1. 핵심 트렌드 및 패턴 식별
2. 원인과 결과 관계 분석  
3. 잠재적 영향 및 시사점 도출
4. 근거 기반 결론 제시

**출력 형식:**
[분석 결과]
- 심층적이고 통찰력 있는 분석 내용
- 데이터 기반의 객관적 분석

[근거 및 출처]
- 분석에 사용된 주요 근거들
- 출처 정보 포함 (Researcher가 제공한 출처 활용)

[결론]
- 명확하고 실행 가능한 결론
- 신뢰도와 한계점 명시

**인용 필수:**
- 모든 분석은 반드시 근거를 제시해야 합니다
- Researcher가 제공한 출처 정보를 활용하세요
- 출처 없이 추측이나 의견만으로 분석하지 마세요"""

    analyst_agent = create_agent(
        llm,
        [],
        analyst_system_prompt,
        use_react=False,
    )
    logger.info("[graph] 노드 생성: researcher, analyst, supervisor")

    workflow = StateGraph(AgentState)
    workflow.add_node("researcher", lambda state: agent_node(state, researcher_agent, "researcher"))
    workflow.add_node("analyst", lambda state: agent_node(state, analyst_agent, "analyst"))
    
    supervisor_chain = create_supervisor(llm, ["researcher", "analyst"])
    workflow.add_node("supervisor", supervisor_chain)

    workflow.add_edge("researcher", "supervisor")
    # Analyst 결과는 최종 답변으로 간주하여 종료로 연결
    workflow.add_edge("analyst", END)
    
    def route_action(state):
        messages = state["messages"]
        last_message = messages[-1]
        content = getattr(last_message, "content", "") or ""
        
        logger.info("[route_action] 분석 중: %s", content[:100])
        
        if isinstance(content, str):
            upper = content.strip().upper()
            
            # 엄격한 ROUTE: 패턴 매칭
            if upper.startswith("ROUTE:"):
                route = upper.split(":", 1)[1].strip()
                logger.info("[route_action] ROUTE 감지: %s", route)
                
                if route == "RESEARCHER":
                    return "researcher"
                elif route == "ANALYST":
                    return "analyst"
                elif route == "END":
                    return END
                else:
                    # 잘못된 ROUTE 값 - 안전하게 종료
                    logger.warning("[route_action] 잘못된 ROUTE 값: %s, 안전 종료", route)
                    return END
            
            # Final Answer: 패턴 (규칙 위반이지만 호환성 유지)
            elif upper.startswith("FINAL ANSWER:"):
                logger.warning("[route_action] Final Answer 패턴 감지 (규칙 위반)")
                stripped = content[len("Final Answer:"):].strip()
                if stripped.lower().startswith("route:"):
                    route = stripped.split(":", 1)[1].strip().lower()
                    if route == "researcher":
                        return "researcher"
                    elif route == "analyst":
                        return "analyst"
                    elif route == "end":
                        return END
                # Final Answer 내용이 있으면 Analyst로 전달
                if stripped:
                    return "analyst"
                return END
            
            # 근거 부족 감지 시 Researcher로 재라우팅
            elif "추가 검색 필요" in content or "근거가 부족" in content:
                logger.info("[route_action] 근거 부족 감지, Researcher로 재라우팅")
                return "researcher"
            
            # 규칙 외 출력 - 안전하게 종료
            elif upper:
                logger.warning("[route_action] 규칙 외 출력 감지: %s, 안전 종료", content[:50])
                return END
        
        # 빈 내용이거나 예상치 못한 형식 - 안전하게 종료
        logger.warning("[route_action] 예상치 못한 형식, 안전 종료")
        return END

    workflow.add_conditional_edges("supervisor", route_action)
    workflow.set_entry_point("supervisor")

    # 재귀 한도 설정으로 무한 루프 방지
    compiled_graph = workflow.compile()
    logger.info("[graph] 재귀 한도 설정: %d", MAX_ITERATIONS)
    
    return compiled_graph

# ==============================================================================
# 6. Streamlit UI 구현 (파일 업로드 기능 추가)
# ==============================================================================
def main():
    st.set_page_config(page_title="🏦 AI 한국은행 경제 분석팀", page_icon="🤖")
    
    os.makedirs(DATA_DIR, exist_ok=True)

    # 업로더 상태 초기화용 키 설정 (업로드 처리 후 키를 변경해 위젯 상태를 리셋)
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    with st.sidebar:
        st.header("📚 참고 자료 관리")
        
        # 웹검색 토글
        web_search_enabled = st.toggle("🌐 웹검색 활성화", value=True, help="웹에서 최신 정보를 검색합니다")
        if "web_search_enabled" not in st.session_state:
            st.session_state.web_search_enabled = True
        st.session_state.web_search_enabled = web_search_enabled
        
        # 그래프 재구성 유틸리티
        def _rebuild_graph():
            st.session_state.pop("agent_graph", None)
            st.session_state.pop("agent_graph_version", None)
            st.cache_resource.clear()
            st.rerun()
        st.button("🔄 그래프 재구성", on_click=_rebuild_graph)
        uploaded_files = st.file_uploader(
            "분석에 참고할 PDF 파일을 업로드하세요.",
            type="pdf",
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}"
        )
        
        if uploaded_files:
            file_added = False
            for uploaded_file in uploaded_files:
                file_path = os.path.join(DATA_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_added = True
            if file_added:
                st.success(f"{len(uploaded_files)}개의 파일이 추가되었습니다. RAG 파이프라인을 업데이트합니다.")
                # 업로더 위젯 상태를 초기화하기 위해 키를 변경 후 재실행
                st.session_state.uploader_key += 1
                st.cache_resource.clear()
                st.rerun()
        st.divider()
        st.subheader("현재 참고 중인 자료")
        pdf_files_in_data = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
        if pdf_files_in_data:
            for f in pdf_files_in_data:
                st.info(f"📄 {os.path.basename(f)}")
        else:
            st.info("업로드된 파일이 없습니다. 기본 데이터로 분석합니다.")
        
        st.divider()
        st.subheader("💬 대화 관리")
        
        # 대화 초기화
        if st.button("🔄 대화 초기화", help="현재 대화를 모두 지웁니다"):
            st.session_state["messages"] = [{"role": "assistant", "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"}]
            st.rerun()
        
        # 대화 내보내기
        def export_conversation():
            messages = st.session_state.get("messages", [])
            if len(messages) > 1:  # 초기 메시지 외에 대화가 있는 경우
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"대화내역_{timestamp}.txt"
                
                export_content = f"AI 한국은행 경제 분석팀 - 대화 내역\n"
                export_content += f"생성일시: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                export_content += f"웹검색 활성화: {'예' if st.session_state.get('web_search_enabled', True) else '아니오'}\n"
                export_content += f"참고자료: {len(pdf_files_in_data)}개\n"
                export_content += "=" * 50 + "\n\n"
                
                for msg in messages:
                    role = "사용자" if msg["role"] == "user" else "AI 분석팀"
                    export_content += f"[{role}]\n{msg['content']}\n\n"
                
                # 파일 다운로드
                st.download_button(
                    label="📥 대화 내보내기",
                    data=export_content,
                    file_name=filename,
                    mime="text/plain",
                    help="현재 대화를 텍스트 파일로 다운로드합니다"
                )
            else:
                st.warning("내보낼 대화가 없습니다.")
        
        export_conversation()

    st.title("🏦 AI 한국은행 경제 분석팀 (LangGraph v0.3.x)")
    st.markdown("멀티 에이전트가 협력하여 질문에 대한 심층 분석을 제공합니다.")
    
    try:
        setup_environment()
        model_factory = AzureModelFactory()

        if ("agent_graph" not in st.session_state) or (st.session_state.get("agent_graph_version") != APP_GRAPH_VERSION):
            # 단계별 시각화가 가능한 상태 패널로 초기화 과정을 표시
            try:
                with st.status("AI 분석팀을 구성하는 중입니다...", expanded=True) as status:
                    # 1) LLM 초기화
                    if status:
                        status.update(label="🧠 LLM 초기화", state="running")
                    llm = model_factory.get_chat_model()
                    st.write("- AzureChatOpenAI 인스턴스 생성 완료")
                    logger.info("[init] LLM 초기화 완료")

                    # 2) RAG 파이프라인 구축 단계별 표시 (캐시 키 도입으로 반복 방지)
                    if status:
                        status.update(label="📚 RAG 파이프라인 구축: PDF 스캔", state="running")
                    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
                    st.write(f"- PDF 파일 수집: {len(pdf_files)}개 발견")
                    logger.info("[init] PDF 스캔: %d개", len(pdf_files))

                    all_docs = []
                    if not pdf_files:
                        st.sidebar.warning("참고 자료가 없습니다. 기본 데이터로 분석합니다.")
                        from langchain_core.documents import Document
                        all_docs = [Document(page_content="[문서 1: 2025년 8월 통화정책방향 결정문 (가상)]\n- 제목: 한국은행 금융통화위원회, 기준금리 현 3.50%로 동결 결정\n- 결정 배경: 소비자물가 상승률이 2%대 후반으로 둔화되었으나, 여전히 높은 수준의 가계부채와 부동산 PF 부실 위험 등 금융안정 리스크가 상존하고 있음을 고려.")]
                    else:
                        if status:
                            status.update(label="📚 RAG 파이프라인 구축: PDF 로딩", state="running")
                        loaded_count = 0
                        for pdf_path in pdf_files:
                            try:
                                loader = PyMuPDFLoader(pdf_path)
                                docs = loader.load()
                                all_docs.extend(docs)
                                loaded_count += 1
                                st.write(f"- 로드 완료: {os.path.basename(pdf_path)} ({len(docs)} 페이지)")
                            except Exception as e:
                                st.sidebar.error(f"'{os.path.basename(pdf_path)}' 파일 로드 실패: {e}")
                                logger.exception("[init] PDF 로드 실패: %s", os.path.basename(pdf_path))
                        st.write(f"- PDF 로딩 요약: {loaded_count}/{len(pdf_files)}개 로딩 완료, 총 문서 {len(all_docs)}개")

                    if not all_docs:
                        raise ValueError("RAG를 위한 문서를 로드할 수 없습니다.")

                    if status:
                        status.update(label="✂️ 텍스트 분할", state="running")
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                    split_docs = text_splitter.split_documents(all_docs)
                    st.write(f"- 분할 완료: 총 청크 {len(split_docs)}개")
                    logger.info("[init] 텍스트 분할: chunks=%d", len(split_docs))

                    if status:
                        status.update(label="🔡 임베딩 생성 및 벡터 저장소 구축", state="running")
                    # 캐시 키: 모델/버전 + PDF 목록 해시
                    import hashlib
                    def _file_sig(path: str) -> str:
                        try:
                            return f"{os.path.basename(path)}:{int(os.path.getmtime(path))}"
                        except Exception:
                            return os.path.basename(path)
                    key_src = APP_GRAPH_VERSION + "|" + ",".join(sorted([_file_sig(p) for p in pdf_files]))
                    cache_key = hashlib.sha256(key_src.encode()).hexdigest()

                    if status:
                        status.update(label="🔡 임베딩/벡터 구축(캐시 적용)", state="running")
                    retriever = build_rag_pipeline(cache_key)
                    st.write("- RAG 리트리버 준비 완료(캐시 활용)")
                    logger.info("[init] RAG 리트리버 준비 완료 (cache_key=%s)", cache_key)

                    # 3) 그래프 생성
                    if status:
                        status.update(label="🕸️ LangGraph 그래프 컴파일", state="running")
                    st.session_state.agent_graph = create_graph(model_factory.get_chat_model(), retriever)
                    st.session_state.agent_graph_version = APP_GRAPH_VERSION
                    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"}]
                    if status:
                        status.update(label="✅ 초기화 완료", state="complete")
                    logger.info("[init] 그래프 컴파일 완료")
            except Exception as e:
                logger.exception("[init] 초기화 중 오류 발생")
                st.error(f"초기화 중 오류가 발생했습니다: {e}")
                return

        messages = st.session_state.get("messages", [])
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("기준금리, 경제 전망 등에 대해 질문하세요."):
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            st.session_state["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                try:
                    with st.status("분석팀이 작업을 시작합니다...") as status:
                        final_response = ""
                        accumulated_messages = []
                        for chunk in st.session_state.agent_graph.stream({"messages": [HumanMessage(content=prompt)]}, config={"recursion_limit": MAX_ITERATIONS}, stream_mode="updates"):
                            logger.debug("[run] chunk=%s", chunk)
                            
                            # Supervisor 단계 처리
                            if "supervisor" in chunk:
                                if status:
                                    status.update(label="🧠 Supervisor가 다음 단계를 결정 중입니다...")
                                logger.info("[run] supervisor 단계")
                                if supervisor_messages := chunk["supervisor"].get("messages"):
                                    last_supervisor_msg = supervisor_messages[-1]
                                    content = getattr(last_supervisor_msg, "content", "").strip()
                                    if content.startswith("Final Answer:"):
                                        final_response = content.replace("Final Answer:", "").strip()
                                        logger.info("[run] Supervisor Final Answer 수집: %s", final_response[:100])
                                    elif content:
                                        accumulated_messages.append(content)
                            
                            # Researcher 단계 처리
                            if "researcher" in chunk:
                                if status:
                                    status.update(label="🔍 Researcher가 정보를 수집하고 있습니다...")
                                logger.info("[run] researcher 단계")
                                if researcher_messages := chunk["researcher"].get("messages"):
                                    content = getattr(researcher_messages[-1], "content", "").strip()
                                    if content:
                                        accumulated_messages.append(content)
                                        # 웹검색 상태 표시
                                        if "웹검색이 비활성화" in content:
                                            st.info("ℹ️ 웹검색이 비활성화되어 있습니다. 최신 정보 수집이 제한됩니다.")
                                        elif "웹 검색 결과" in content:
                                            st.success("✅ 웹에서 최신 정보를 수집했습니다.")
                            
                            # Analyst 단계 처리 - 최종 응답 우선 수집
                            if "analyst" in chunk:
                                if status:
                                    status.update(label="✍️ Analyst가 데이터를 분석하고 보고서를 작성 중입니다...")
                                logger.info("[run] analyst 단계")
                                if analyst_messages := chunk["analyst"].get("messages"):
                                    final_msg = analyst_messages[-1]
                                    content = getattr(final_msg, "content", "").strip()
                                    if content:
                                        final_response = content
                                        accumulated_messages.append(content)
                                        logger.info("[run] Analyst 최종 응답 수집: %s", final_response[:100])
                            
                            # 전체 메시지 스트림에서 보강 수집
                            if messages := chunk.get("messages"):
                                last = messages[-1]
                                last_content = getattr(last, "content", "").strip()
                                last_name = getattr(last, "name", "")
                                
                                # Supervisor의 Final Answer 처리
                                if last_content.startswith("Final Answer:"):
                                    cleaned = last_content.replace("Final Answer:", "").strip()
                                    if not cleaned.upper().startswith("ROUTE:"):
                                        final_response = cleaned
                                        logger.info("[run] 전체 스트림에서 Final Answer 수집: %s", final_response[:100])
                                
                                # Analyst 메시지 처리 (Supervisor Final Answer가 없을 때)
                                elif last_name == "analyst" and last_content:
                                    if not final_response:  # 아직 최종 응답이 없으면 Analyst 응답 사용
                                        final_response = last_content
                                        logger.info("[run] 전체 스트림에서 Analyst 응답 수집: %s", final_response[:100])
                                    accumulated_messages.append(last_content)

                        # 최종 응답이 비어있을 때 폴백 처리
                        if not final_response and accumulated_messages:
                            final_response = accumulated_messages[-1]
                            logger.info("[run] 폴백: 누적 메시지에서 최종 응답 수집: %s", final_response[:100])
                        
                        # 최종 응답 검증
                        if not final_response:
                            final_response = "분석이 완료되었으나 응답을 생성하지 못했습니다. 다시 시도해주세요."
                            logger.warning("[run] 최종 응답이 비어있음 - 기본 메시지 사용")
                        
                        logger.info("[run] 최종 응답 준비 완료 (길이=%d): %s", len(final_response), final_response[:100])
                        
                        # 근거 미리보기 추출 및 표시
                        preview_sources = extract_preview_sources(final_response)
                        if preview_sources:
                            with st.expander("📋 근거 미리보기", expanded=False):
                                st.markdown("**주요 근거 정보:**")
                                for i, source in enumerate(preview_sources[:3], 1):
                                    st.markdown(f"**{i}.** {source}")
                        
                        if status:
                            status.update(label="✅ 분석 완료!", state="complete")
                except Exception as e:
                    logger.exception("[run] 상태 업데이트 중 오류")
                    final_response = "분석 중 오류가 발생했습니다. 다시 시도해주세요."

                st.write(final_response)
                logger.info("[run] 최종 응답 길이=%d", len(final_response))
                if "messages" not in st.session_state:
                    st.session_state["messages"] = []
                st.session_state["messages"].append({"role": "assistant", "content": final_response})

    except Exception as e:
        logger.exception("[app] 전역 오류")
        st.error(f"오류가 발생했습니다: {str(e)}")

# ==============================================================================
# 7. 애플리케이션 실행 (Application Execution)
# ==============================================================================
if __name__ == "__main__":
    main()

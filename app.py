# ==============================================================================
# 1. 라이브러리 임포트 (Imports & Setup)
# ==============================================================================
# 최신 LangChain v0.2.x 및 v0.3.x 버전에 맞춰 모듈화된 라이브러리들을 임포트합니다.
import os
import logging
import json
import glob
import streamlit as st
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List
from langchain_core.messages import HumanMessage, ToolMessage

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
            max_retries=3,
            timeout=30,
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
    """
    try:
        logger.info("[web-search] query='%s'", query)
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
        logger.exception("[web-search] 오류")
        return f"웹 검색 중 오류가 발생했습니다: {e}"


# ==============================================================================
# 3. 고급 RAG 파이프라인 구축 (Advanced RAG Pipeline with Dynamic PDF Loading)
# ==============================================================================
@st.cache_resource
def build_rag_pipeline(cache_key: str):
    """
    'data' 폴더 내의 모든 PDF를 동적으로 로드하여 RAG 파이프라인을 구축합니다.
    _model_factory 인자는 캐싱에서 제외됩니다.
    """
    logger.info("[rag] 파이프라인 빌드 시작 (cache_key=%s)", cache_key)
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
    vectorstore = FAISS.from_documents(documents=split_docs, embedding=embeddings)
    logger.info("[rag] FAISS 벡터스토어 생성 완료")

    from langchain_openai import AzureChatOpenAI
    chat_deploy = os.getenv("AOAI_DEPLOY_GPT4O")
    llm = AzureChatOpenAI(
        azure_deployment=chat_deploy,
        api_version=AZURE_API_VERSION,
        azure_endpoint=endpoint,
        api_key=api_key,
        temperature=0,
    )
    retriever = MultiQueryRetriever.from_llm(retriever=vectorstore.as_retriever(), llm=llm)
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
        # ReAct + Tool-Calling 전용 프롬프트 (MessagesPlaceholder 사용)
        prompt = (
            ChatPromptTemplate.from_messages([
                (
                    "system",
                    "{system_prompt}\n\n사용 가능한 도구:\n{tools}\n\n도구 이름 목록: {tool_names}"
                ),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            .partial(system_prompt=system_prompt, tools=tools_desc, tool_names=tool_names)
        )
        agent = create_react_agent(llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            handle_parsing_errors="오류 발생: 분석을 재시도하세요.",
            verbose=True,
        )

    # 도구가 없거나(use_react=False) 최종 응답만 원하는 경우: 일반 LLM 체인
    from langchain_core.output_parsers import StrOutputParser
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}\n\n요청에 대해 최종 답변만 생성하세요. 불필요한 사고과정이나 도구 호출 지시문을 출력하지 마세요. 항상 구체적인 결론을 포함한 한국어 최종 답변을 간결히 작성하세요."),
        ("human", "{input}")
    ]).partial(system_prompt=system_prompt)
    runnable = prompt | llm | StrOutputParser()
    return _SimpleAgentExecutor(runnable)

def agent_node(state, agent, name):
    try:
        last_message = state["messages"][-1]
        # 1) Supervisor 라우팅 지시문은 워커 입력으로 사용하지 않음
        if isinstance(getattr(last_message, "content", ""), str):
            content_upper = last_message.content.strip().upper()
            if content_upper.startswith("ROUTE:") or content_upper.startswith("FINAL ANSWER:"):
                logger.info("[agent-node:%s] 라우팅 지시문 감지, 실행 스킵", name)
                return {"messages": []}
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
                # AgentExecutor가 scratchpad를 관리하도록 입력만 전달
                invoke_result = agent.invoke({"input": worker_input or ""})
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
            invoke_result = agent.invoke({"input": worker_input or ""})
            result_text = invoke_result.get("output", "")
        else:
            # _SimpleAgentExecutor 등 일반 체인: invoke가 dict 반환하도록 래핑됨
            result_text = agent.invoke({"input": worker_input or ""}).get("output", "")
        return {"messages": [HumanMessage(content=result_text, name=name)]}
    except Exception as e:
        logger.exception("[agent-node:%s] 오류", name)
        error_message = f"Error in {name} Agent: {e}"
        return {"messages": [HumanMessage(content=error_message, name="error")]}

def create_supervisor(llm: AzureChatOpenAI, agent_names: List[str]):
    system_prompt = (
        "당신은 여러 AI 에이전트를 관리하는 감독관입니다.\n"
        "다음 중 하나만 정확히 출력하세요:\n"
        "- ROUTE: researcher\n- ROUTE: analyst\n- ROUTE: END\n"
        "최종 답변이 바로 필요할 때만 'Final Answer: '로 시작해 한 번만 출력하세요.\n"
        "그 외 모든 설명/생각/JSON/도구호출은 금지합니다."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        MessagesPlaceholder(variable_name="messages"),
    ]).partial(system_prompt=system_prompt)

    def supervisor_node(state):
        messages = state.get("messages", []) if isinstance(state, dict) else []
        logger.info("[supervisor] 입력 메시지 수=%d", len(messages))
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
    researcher_agent = create_agent(
        llm,
        researcher_tools,
        "당신은 전문 경제 연구원입니다. 사용자의 요청에 따라 제공된 문서와 웹에서 정확하고 객관적인 정보를 찾아서 제공하는 역할을 합니다.",
        use_react=True,
    )
    analyst_agent = create_agent(
        llm,
        [],
        "당신은 날카로운 통찰력을 가진 경제 분석가입니다. 주어진 데이터(context)를 바탕으로 사용자의 질문에 대한 깊이 있는 분석과 명확한 답변을 생성합니다.",
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
        # Supervisor가 ROUTE: ... 또는 Final Answer 를 출력
        content = getattr(last_message, "content", "") or ""
        if isinstance(content, str):
            upper = content.strip()
            if upper.startswith("Final Answer:"):
                return END
            if upper.startswith("ROUTE:"):
                route = upper.split(":", 1)[1].strip().lower()
                if route == "researcher":
                    return "researcher"
                if route == "analyst":
                    return "analyst"
                if route == "end":
                    return END
            # 'Final Answer' 접두사 없이 결론만 준 경우, analyst로 보내 최종화 시도
            if upper and not upper.startswith("ROUTE:"):
                return "analyst"
        # 기본은 종료로 처리하여 재귀 루프 차단
        return END

    workflow.add_conditional_edges("supervisor", route_action)
    workflow.set_entry_point("supervisor")

    return workflow.compile()

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

    st.title("🏦 AI 한국은행 경제 분석팀 (LangGraph v0.3.x)")
    st.markdown("멀티 에이전트가 협력하여 질문에 대한 심층 분석을 제공합니다.")
    
    try:
        setup_environment()
        model_factory = AzureModelFactory()

        if ("agent_graph" not in st.session_state) or (st.session_state.get("agent_graph_version") != APP_GRAPH_VERSION):
            # 단계별 시각화가 가능한 상태 패널로 초기화 과정을 표시
            with st.status("AI 분석팀을 구성하는 중입니다...", expanded=True) as status:
                # 1) LLM 초기화
                status.update(label="🧠 LLM 초기화", state="running")
                llm = model_factory.get_chat_model()
                st.write("- AzureChatOpenAI 인스턴스 생성 완료")
                logger.info("[init] LLM 초기화 완료")

                # 2) RAG 파이프라인 구축 단계별 표시 (캐시 키 도입으로 반복 방지)
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

                status.update(label="✂️ 텍스트 분할", state="running")
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                split_docs = text_splitter.split_documents(all_docs)
                st.write(f"- 분할 완료: 총 청크 {len(split_docs)}개")
                logger.info("[init] 텍스트 분할: chunks=%d", len(split_docs))

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

                status.update(label="🔡 임베딩/벡터 구축(캐시 적용)", state="running")
                retriever = build_rag_pipeline(cache_key)
                st.write("- RAG 리트리버 준비 완료(캐시 활용)")
                logger.info("[init] RAG 리트리버 준비 완료 (cache_key=%s)", cache_key)

                # 3) 그래프 생성
                status.update(label="🕸️ LangGraph 그래프 컴파일", state="running")
                st.session_state.agent_graph = create_graph(model_factory.get_chat_model(), retriever)
                st.session_state.agent_graph_version = APP_GRAPH_VERSION
                st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"}]
                status.update(label="✅ 초기화 완료", state="complete")
                logger.info("[init] 그래프 컴파일 완료")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("기준금리, 경제 전망 등에 대해 질문하세요."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.status("분석팀이 작업을 시작합니다...") as status:
                    final_response = ""
                    accumulated_messages = []
                    for chunk in st.session_state.agent_graph.stream({"messages": [HumanMessage(content=prompt)]}, config={"recursion_limit": 50}, stream_mode="values"):
                        logger.debug("[run] chunk=%s", chunk)
                        if "supervisor" in chunk:
                            status.update(label="🧠 Supervisor가 다음 단계를 결정 중입니다...")
                            logger.info("[run] supervisor 단계")
                            if supervisor_messages := chunk["supervisor"].get("messages"):
                                last_supervisor_msg = supervisor_messages[-1]
                                content = getattr(last_supervisor_msg, "content", "").strip()
                                if content.startswith("Final Answer:"):
                                    final_response = content.replace("Final Answer:", "").strip()
                                elif content:
                                    accumulated_messages.append(content)
                        if "researcher" in chunk:
                            status.update(label="🔍 Researcher가 정보를 수집하고 있습니다...")
                            logger.info("[run] researcher 단계")
                            if researcher_messages := chunk["researcher"].get("messages"):
                                content = getattr(researcher_messages[-1], "content", "").strip()
                                if content:
                                    accumulated_messages.append(content)
                        if "analyst" in chunk:
                            status.update(label="✍️ Analyst가 데이터를 분석하고 보고서를 작성 중입니다...")
                            logger.info("[run] analyst 단계")
                            if analyst_messages := chunk["analyst"].get("messages"):
                                final_msg = analyst_messages[-1]
                                content = getattr(final_msg, "content", "").strip()
                                if content:
                                    final_response = content
                                    accumulated_messages.append(content)
                    if not final_response and accumulated_messages:
                        final_response = accumulated_messages[-1]
                    
                    status.update(label="✅ 분석 완료!", state="complete")

                st.write(final_response)
                logger.info("[run] 최종 응답 길이=%d", len(final_response))
                st.session_state.messages.append({"role": "assistant", "content": final_response})

    except Exception as e:
        logger.exception("[app] 전역 오류")
        st.error(f"오류가 발생했습니다: {str(e)}")

# ==============================================================================
# 7. 애플리케이션 실행 (Application Execution)
# ==============================================================================
if __name__ == "__main__":
    main()

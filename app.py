# ==============================================================================
# 1. 라이브러리 임포트 (Imports & Setup)
# ==============================================================================
# 최신 LangChain v0.2.x 및 v0.3.x 버전에 맞춰 모듈화된 라이브러리들을 임포트합니다.
import os
import glob
import streamlit as st
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, AnyMessageEditor, HumanMessage

# LangGraph 및 에이전트 관련
from langgraph.graph import StateGraph, END
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool

# Azure OpenAI 및 RAG 관련
from langchain_azure_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader # PDF 로더 변경
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_query import MultiQueryRetriever
from ddgs import DDGS # ddgs 라이브러리로 변경


# ==============================================================================
# 2. 환경설정 및 API 키 관리 (Configuration & API Keys)
# ==============================================================================
def setup_environment():
    """환경 변수를 로드하고 필수 변수가 설정되었는지 확인합니다."""
    load_dotenv()
    required_vars = ["AOAI_ENDPOINT", "AOAI_API_KEY", "AOAI_DEPLOY_GPT4O", "AOAI_DEPLOY_EMBED_3_LARGE"]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"환경 변수 '{var}'가 설정되지 않았습니다. .env 파일을 확인하세요.")

AZURE_API_VERSION = "2024-02-01"
DATA_DIR = "data" # 업로드된 PDF를 저장할 디렉토리

# ==============================================================================
# 2.5. ddgs 기반 웹 검색 도구 정의 (New Web Search Tool)
# ==============================================================================
def web_search_func(query: str, max_results: int = 5) -> str:
    """
    ddgs 라이브러리를 사용하여 DuckDuckGo 웹 검색을 수행하고 결과를 포맷팅합니다.
    """
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            if not results:
                return "검색 결과가 없습니다."
            
            formatted_results = []
            for i, res in enumerate(results, 1):
                formatted_results.append(f"결과 {i}: {res['title']}\n요약: {res['body']}\nURL: {res['href']}\n---")
            return "\n".join(formatted_results)
    except Exception as e:
        return f"웹 검색 중 오류가 발생했습니다: {e}"


# ==============================================================================
# 3. 고급 RAG 파이프라인 구축 (Advanced RAG Pipeline with Dynamic PDF Loading)
# ==============================================================================
@st.cache_resource
def build_rag_pipeline(_llm: AzureChatOpenAI):
    """
    'data' 폴더 내의 모든 PDF를 동적으로 로드하여 RAG 파이프라인을 구축합니다.
    """
    all_docs = []
    
    # 1. data 폴더에서 모든 PDF 파일 스캔 및 로드
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    
    if not pdf_files:
        st.sidebar.warning("참고 자료가 없습니다. 기본 데이터로 분석합니다.")
        # data 폴더에 파일이 없을 경우, 기본 가상 데이터를 사용
        docs_content = """
        [문서 1: 2025년 8월 통화정책방향 결정문 (가상)]
        - 제목: 한국은행 금융통화위원회, 기준금리 현 3.50%로 동결 결정
        - 결정 배경: 소비자물가 상승률이 2%대 후반으로 둔화되었으나, 여전히 높은 수준의 가계부채와 부동산 PF 부실 위험 등 금융안정 리스크가 상존하고 있음을 고려.
        """
        # 임시 텍스트를 Document 객체로 변환
        from langchain_core.documents import Document
        all_docs = [Document(page_content=docs_content)]
    else:
        for pdf_path in pdf_files:
            try:
                loader = PyMuPDFLoader(pdf_path)
                all_docs.extend(loader.load())
            except Exception as e:
                st.sidebar.error(f"'{os.path.basename(pdf_path)}' 파일 로드 실패: {e}")

    if not all_docs:
         raise ValueError("RAG를 위한 문서를 로드할 수 없습니다.")

    # 2. 텍스트 분할
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = text_splitter.split_documents(all_docs)

    # 3. 임베딩 및 Vector DB 저장
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("AOAI_DEPLOY_EMBED_3_LARGE"),
        api_version=AZURE_API_VERSION,
    )
    vectorstore = FAISS.from_documents(documents=split_docs, embedding=embeddings)

    # 4. 고급 검색기 생성 (MultiQueryRetriever)
    retriever = MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(), llm=_llm
    )
    return retriever

# ==============================================================================
# 4. 멀티 에이전트 정의 (Multi-Agent Definition)
# ==============================================================================
class AgentState(TypedDict):
    messages: Annotated[list, AnyMessageEditor]

def create_agent(llm: AzureChatOpenAI, tools: list, system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, verbose=True)

def agent_node(state, agent, name):
    try:
        result = agent.invoke(state)
        return {"messages": [HumanMessage(content=result["output"], name=name)]}
    except Exception as e:
        error_message = f"Error in {name} Agent: {e}"
        return {"messages": [HumanMessage(content=error_message, name="error")]}

def create_supervisor(llm: AzureChatOpenAI, agent_names: List[str]):
    system_prompt = (
        "당신은 여러 AI 에이전트를 관리하는 감독관입니다. "
        "사용자의 요청을 분석하여 아래의 워커 에이전트 중 가장 적합한 에이전트에게 작업을 할당하세요. "
        "작업은 한 번에 하나의 에이전트에게만 할당해야 합니다. 각 워커가 작업을 마치면 그 결과를 바탕으로 다음 단계를 결정하세요. "
        "만약 'error' 이름으로 메시지를 받으면, 해당 에이전트가 작업에 실패한 것입니다. 상황을 파악하여 다른 에이전트에게 작업을 재할당하거나, 사용자에게 문제를 설명하고 작업을 종료하세요."
        "모든 작업이 완료되었다고 판단되면, 최종 답변을 종합하여 사용자에게 'Final Answer:' 접두사를 붙여 제공하세요."
        "\n\n사용 가능한 에이전트:\n"
        f"{', '.join(agent_names)}"
    )
    tools = [Tool(name=name, func=lambda x: x, description=f"{name} 에이전트에게 작업을 위임합니다.") for name in agent_names]
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("placeholder", "{messages}")])
    return llm.bind_tools(tools)

# ==============================================================================
# 5. LangGraph 그래프 구성 (Graph Construction)
# ==============================================================================
def create_graph(llm, retriever):
    researcher_tools = [
        Tool(name="bok_document_search", func=retriever.invoke, description="사용자가 업로드한 PDF 문서나 한국은행 공식 문서를 검색하여 특정 경제 용어, 정책, 보고서 내용을 찾습니다."),
        Tool(name="web_search", func=web_search_func, description="최신 경제 뉴스나 실시간 시장 반응 등 현재 정보를 위해 웹을 검색합니다.")
    ]
    researcher_agent = create_agent(llm, researcher_tools, "당신은 전문 경제 연구원입니다. 사용자의 요청에 따라 제공된 문서와 웹에서 정확하고 객관적인 정보를 찾아서 제공하는 역할을 합니다.")
    analyst_agent = create_agent(llm, [], "당신은 날카로운 통찰력을 가진 경제 분석가입니다. 주어진 데이터(context)를 바탕으로 사용자의 질문에 대한 깊이 있는 분석과 명확한 답변을 생성합니다.")

    workflow = StateGraph(AgentState)
    workflow.add_node("researcher", lambda state: agent_node(state, researcher_agent, "researcher"))
    workflow.add_node("analyst", lambda state: agent_node(state, analyst_agent, "analyst"))
    
    supervisor_llm = create_supervisor(llm, ["researcher", "analyst"])
    workflow.add_node("supervisor", supervisor_llm)

    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("analyst", "supervisor")
    
    def route_action(state):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            tool_name = last_message.tool_calls[0]['name'].lower()
            if "researcher" in tool_name: return "researcher"
            if "analyst" in tool_name: return "analyst"
        return END

    workflow.add_conditional_edges("supervisor", route_action)
    workflow.set_entry_point("supervisor")

    return workflow.compile()

# ==============================================================================
# 6. Streamlit UI 구현 (파일 업로드 기능 추가)
# ==============================================================================
def main():
    st.set_page_config(page_title="🏦 AI 한국은행 경제 분석팀", page_icon="🤖")
    
    # --- 데이터 디렉토리 생성 ---
    os.makedirs(DATA_DIR, exist_ok=True)

    # --- 사이드바 UI ---
    with st.sidebar:
        st.header("📚 참고 자료 관리")
        
        uploaded_files = st.file_uploader(
            "분석에 참고할 PDF 파일을 업로드하세요.",
            type="pdf",
            accept_multiple_files=True
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


    # --- 메인 채팅 UI ---
    st.title("🏦 AI 한국은행 경제 분석팀 (LangGraph v0.3.x)")
    st.markdown("멀티 에이전트가 협력하여 질문에 대한 심층 분석을 제공합니다.")
    
    try:
        setup_environment()

        if "agent_graph" not in st.session_state:
            with st.spinner("AI 분석팀을 구성하는 중입니다..."):
                llm = AzureChatOpenAI(azure_deployment=os.getenv("AOAI_DEPLOY_GPT4O"), api_version=AZURE_API_VERSION, temperature=0)
                retriever = build_rag_pipeline(llm)
                st.session_state.agent_graph = create_graph(llm, retriever)
                st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 저는 경제 분석을 돕는 AI 분석팀입니다. 무엇이 궁금하신가요?"}]

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
                    for chunk in st.session_state.agent_graph.stream({"messages": [HumanMessage(content=prompt)]}, stream_mode="values"):
                        if "supervisor" in chunk:
                            status.update(label="🧠 Supervisor가 다음 단계를 결정 중입니다...")
                            if supervisor_messages := chunk["supervisor"].get("messages"):
                                last_supervisor_msg = supervisor_messages[-1]
                                if not last_supervisor_msg.tool_calls:
                                    final_response = last_supervisor_msg.content.replace("Final Answer:", "").strip()
                        if "researcher" in chunk:
                            status.update(label="🔍 Researcher가 정보를 수집하고 있습니다...")
                        if "analyst" in chunk:
                            status.update(label="✍️ Analyst가 데이터를 분석하고 보고서를 작성 중입니다...")
                    
                    status.update(label="✅ 분석 완료!", state="complete")

                st.write(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})

    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

# ==============================================================================
# 7. 애플리케이션 실행 (Application Execution)
# ==============================================================================
if __name__ == "__main__":
    main()

"""
Knowledge Graph Wiki System - Streamlit UI

PRD 요구사항에 맞는 지식 그래프 기반 위키 시스템
- 사이드바 검색
- 그래프 탭·위키 탭
- 드래그·줌
- 다크 모드
- 반응형 레이아웃
- RBAC 기반 권한
"""

import streamlit as st
import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import plotly.graph_objects as go
import networkx as nx
from pathlib import Path

# API 설정
API_BASE_URL = "http://localhost:8000/api/v1"

# 페이지 설정
st.set_page_config(
    page_title="Knowledge Graph Wiki System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
def load_css():
    """다크 모드 및 반응형 레이아웃을 위한 CSS 로드"""
    st.markdown("""
    <style>
    /* 다크 모드 스타일 */
    .dark-mode {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    
    /* 반응형 레이아웃 */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
        }
        .sidebar-content {
            padding: 0.5rem;
        }
    }
    
    /* 그래프 컨테이너 */
    .graph-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* 위키 콘텐츠 */
    .wiki-content {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* 검색 결과 */
    .search-result {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        cursor: pointer;
    }
    
    .search-result:hover {
        background-color: #f0f0f0;
    }
    
    /* 상태 표시 */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-success { background-color: #28a745; }
    .status-error { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
def init_session_state():
    """세션 상태 초기화"""
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "graph"
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'selected_node' not in st.session_state:
        st.session_state.selected_node = None
    if 'graph_data' not in st.session_state:
        st.session_state.graph_data = None
    if 'wiki_content' not in st.session_state:
        st.session_state.wiki_content = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = "user"  # user, editor, admin
    if 'workflow_status' not in st.session_state:
        st.session_state.workflow_status = "idle"

# 사이드바 컴포넌트
def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.header("🔍 검색 및 설정")
        
        # 다크 모드 토글
        dark_mode = st.checkbox("🌙 다크 모드", value=st.session_state.dark_mode)
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()
        
        st.divider()
        
        # 키워드 검색
        st.subheader("키워드 검색")
        search_query = st.text_input(
            "검색할 키워드를 입력하세요",
            value=st.session_state.search_query,
            placeholder="예: 인공지능, 머신러닝, 딥러닝"
        )
        
        if st.button("🔍 검색 시작", type="primary"):
            if search_query.strip():
                st.session_state.search_query = search_query
                start_knowledge_workflow(search_query)
        
        st.divider()
        
        # 필터 설정
        st.subheader("필터 설정")
        entity_types = st.multiselect(
            "엔티티 타입",
            ["PERSON", "ORGANIZATION", "CONCEPT", "LOCATION", "EVENT"],
            default=["PERSON", "ORGANIZATION", "CONCEPT"]
        )
        
        confidence_threshold = st.slider(
            "신뢰도 임계값",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
        
        st.divider()
        
        # 사용자 권한 표시
        st.subheader("👤 사용자 정보")
        user_role = st.selectbox(
            "역할",
            ["user", "editor", "admin"],
            index=0 if st.session_state.user_role == "user" else 1 if st.session_state.user_role == "editor" else 2
        )
        st.session_state.user_role = user_role
        
        # 권한별 기능 표시
        if user_role in ["editor", "admin"]:
            st.success("✅ 편집 권한")
            if st.button("📝 피드백 제출"):
                show_feedback_form()
        else:
            st.info("ℹ️ 읽기 전용")
        
        st.divider()
        
        # 시스템 상태
        st.subheader("⚙️ 시스템 상태")
        status_color = "success" if st.session_state.workflow_status == "idle" else "warning"
        st.markdown(f"""
        <div class="status-indicator status-{status_color}"></div>
        워크플로우: {st.session_state.workflow_status}
        """, unsafe_allow_html=True)

# 지식 그래프 워크플로우 시작
def start_knowledge_workflow(keyword: str):
    """지식 그래프 워크플로우 시작"""
    st.session_state.workflow_status = "running"
    
    try:
        # Supervisor Agent에 워크플로우 요청
        workflow_data = {
            "trace_id": f"workflow_{int(time.time())}",
            "user_id": st.session_state.user_role,
            "request": {
                "keyword": keyword,
                "top_k": 10,
                "extraction_mode": "comprehensive"
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/supervisor/process",
            json=workflow_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.workflow_status = "completed"
            
            # 결과 처리
            if "result" in result:
                process_workflow_result(result["result"])
            
            st.success("✅ 지식 그래프 생성 완료!")
        else:
            st.error(f"❌ 워크플로우 실행 실패: {response.text}")
            st.session_state.workflow_status = "error"
            
    except Exception as e:
        st.error(f"❌ 워크플로우 오류: {str(e)}")
        st.session_state.workflow_status = "error"

# 워크플로우 결과 처리
def process_workflow_result(result: Dict[str, Any]):
    """워크플로우 결과 처리"""
    # 그래프 데이터 저장
    if "graph_data" in result:
        st.session_state.graph_data = result["graph_data"]
    
    # 위키 콘텐츠 저장
    if "wiki_content" in result:
        st.session_state.wiki_content = result["wiki_content"]

# 그래프 탭 렌더링
def render_graph_tab():
    """그래프 탭 렌더링"""
    st.header("🧠 지식 그래프 시각화")
    
    if st.session_state.graph_data is None:
        st.info("🔍 키워드를 검색하여 지식 그래프를 생성하세요.")
        return
    
    # 그래프 컨트롤
    col1, col2, col3 = st.columns(3)
    
    with col1:
        layout_type = st.selectbox(
            "레이아웃",
            ["force_directed", "hierarchical", "circular"],
            index=0
        )
    
    with col2:
        node_limit = st.slider("노드 수 제한", 10, 200, 100)
    
    with col3:
        include_labels = st.checkbox("라벨 표시", value=True)
    
    # 그래프 시각화
    if st.session_state.graph_data:
        try:
            # NetworkX 그래프 생성
            G = nx.Graph()
            
            # 노드 추가
            for node in st.session_state.graph_data.get("nodes", [])[:node_limit]:
                G.add_node(node["id"], **node)
            
            # 엣지 추가
            for edge in st.session_state.graph_data.get("edges", []):
                if edge["source"] in G.nodes and edge["target"] in G.nodes:
                    G.add_edge(edge["source"], edge["target"], **edge)
            
            # 레이아웃 계산
            if layout_type == "force_directed":
                pos = nx.spring_layout(G)
            elif layout_type == "hierarchical":
                pos = nx.kamada_kawai_layout(G)
            else:  # circular
                pos = nx.circular_layout(G)
            
            # Plotly 그래프 생성
            edge_trace = go.Scatter(
                x=[], y=[], line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')
            
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_trace['x'] += tuple([x0, x1, None])
                edge_trace['y'] += tuple([y0, y1, None])
            
            node_trace = go.Scatter(
                x=[], y=[], text=[], mode='markers', hoverinfo='text',
                marker=dict(showscale=True, colorscale='YlGnBu', size=10,
                           colorbar=dict(thickness=15, xanchor="left", titleside="right"),
                           line_width=2))
            
            for node in G.nodes():
                x, y = pos[node]
                node_trace['x'] += tuple([x])
                node_trace['y'] += tuple([y])
                node_trace['text'] += tuple([f"노드: {node}"])
            
            fig = go.Figure(data=[edge_trace, node_trace],
                          layout=go.Layout(
                              title='지식 그래프',
                              showlegend=False,
                              hovermode='closest',
                              margin=dict(b=20,l=5,r=5,t=40),
                              xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                              yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                          )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 그래프 통계
            st.subheader("📊 그래프 통계")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("노드 수", len(G.nodes()))
            with col2:
                st.metric("엣지 수", len(G.edges()))
            with col3:
                st.metric("연결 요소", nx.number_connected_components(G))
            with col4:
                st.metric("평균 차수", round(sum(dict(G.degree()).values()) / len(G.nodes()), 2))
            
        except Exception as e:
            st.error(f"그래프 렌더링 오류: {str(e)}")

# 위키 탭 렌더링
def render_wiki_tab():
    """위키 탭 렌더링"""
    st.header("📚 위키 문서")
    
    if st.session_state.wiki_content is None:
        st.info("🔍 키워드를 검색하여 위키 문서를 생성하세요.")
        return
    
    # 위키 콘텐츠 표시
    wiki_content = st.session_state.wiki_content
    
    # 제목
    if "title" in wiki_content:
        st.title(wiki_content["title"])
    
    # 요약
    if "summary" in wiki_content:
        with st.expander("📝 요약", expanded=True):
            st.write(wiki_content["summary"])
    
    # 메인 콘텐츠
    if "markdown" in wiki_content:
        st.markdown(wiki_content["markdown"])
    
    # 참고 문헌
    if "references" in wiki_content and wiki_content["references"]:
        st.subheader("📖 참고 문헌")
        for i, ref in enumerate(wiki_content["references"], 1):
            st.markdown(f"{i}. {ref.get('title', '제목 없음')}")
            if ref.get('url'):
                st.markdown(f"   URL: {ref['url']}")
    
    # 메타데이터
    if "metadata" in wiki_content:
        with st.expander("ℹ️ 메타데이터"):
            metadata = wiki_content["metadata"]
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**생성 시간:**", metadata.get("created_at", "N/A"))
                st.write("**작성자:**", metadata.get("author", "Wiki Agent"))
            
            with col2:
                st.write("**버전:**", metadata.get("version", "1.0"))
                st.write("**단어 수:**", metadata.get("word_count", "N/A"))

# 피드백 폼 표시
def show_feedback_form():
    """피드백 제출 폼"""
    st.subheader("📝 피드백 제출")
    
    feedback_type = st.selectbox(
        "피드백 타입",
        ["correction", "addition", "deletion", "suggestion"]
    )
    
    feedback_content = st.text_area(
        "피드백 내용",
        placeholder="수정 사항이나 제안사항을 입력하세요..."
    )
    
    if st.button("제출", type="primary"):
        if feedback_content.strip():
            submit_feedback(feedback_type, feedback_content)
        else:
            st.warning("피드백 내용을 입력해주세요.")

# 피드백 제출
def submit_feedback(feedback_type: str, content: str):
    """피드백 제출"""
    try:
        feedback_data = {
            "node_id": st.session_state.selected_node or "general",
            "feedback": content,
            "feedback_type": feedback_type,
            "user_id": st.session_state.user_role
        }
        
        response = requests.post(
            f"{API_BASE_URL}/feedback/process",
            json=feedback_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("acknowledged"):
                st.success("✅ 피드백이 성공적으로 제출되었습니다!")
            else:
                st.warning("⚠️ 피드백 제출에 실패했습니다.")
        else:
            st.error(f"❌ 피드백 제출 오류: {response.text}")
            
    except Exception as e:
        st.error(f"❌ 피드백 제출 오류: {str(e)}")

# 메인 UI 렌더링
def render_main_ui():
    """메인 UI 렌더링"""
    # 헤더
    st.title("🧠 Knowledge Graph Wiki System")
    st.markdown("""
    ### 지식 그래프 기반 위키 시스템
    키워드를 입력하면 자동으로 지식 그래프를 생성하고 위키 문서를 작성합니다.
    """)
    
    # 탭 선택
    tab1, tab2, tab3 = st.tabs(["🧠 지식 그래프", "📚 위키 문서", "📊 시스템 상태"])
    
    with tab1:
        render_graph_tab()
    
    with tab2:
        render_wiki_tab()
    
    with tab3:
        render_system_status()

# 시스템 상태 탭
def render_system_status():
    """시스템 상태 탭"""
    st.header("📊 시스템 상태")
    
    # 워크플로우 상태
    st.subheader("🔄 워크플로우 상태")
    status_color = {
        "idle": "🟢",
        "running": "🟡",
        "completed": "🟢",
        "error": "🔴"
    }.get(st.session_state.workflow_status, "⚪")
    
    st.write(f"{status_color} 현재 상태: {st.session_state.workflow_status}")
    
    # API 상태 확인
    st.subheader("🔌 API 연결 상태")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ API 서버 연결 정상")
        else:
            st.warning("⚠️ API 서버 응답 이상")
    except:
        st.error("❌ API 서버 연결 실패")
    
    # 사용자 정보
    st.subheader("👤 사용자 정보")
    st.write(f"**역할:** {st.session_state.user_role}")
    st.write(f"**현재 선택된 노드:** {st.session_state.selected_node or '없음'}")
    
    # 최근 활동
    st.subheader("📈 최근 활동")
    if st.session_state.search_query:
        st.write(f"**최근 검색:** {st.session_state.search_query}")
    else:
        st.write("검색 기록이 없습니다.")

# 메인 실행
def main():
    """메인 실행 함수"""
    # CSS 로드
    load_css()
    
    # 세션 상태 초기화
    init_session_state()
    
    # 다크 모드 적용
    if st.session_state.dark_mode:
        st.markdown('<div class="dark-mode">', unsafe_allow_html=True)
    
    # 사이드바 렌더링
    render_sidebar()
    
    # 메인 UI 렌더링
    render_main_ui()
    
    # 다크 모드 닫기
    if st.session_state.dark_mode:
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 
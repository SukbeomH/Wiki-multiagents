"""
사이드바 컴포넌트 모듈
"""
import os
import glob
import streamlit as st
from core.config import Config
from core.logger import logger
from core.state_manager import StateManager


def render_sidebar():
    """사이드바를 렌더링합니다."""
    with st.sidebar:
        st.header("📚 참고 자료 관리")
        
        # 그래프 재구성 유틸리티
        def _rebuild_graph():
            StateManager.clear_agent_graph()
            st.cache_resource.clear()
            st.rerun()
        
        st.button("🔄 그래프 재구성", on_click=_rebuild_graph)
        
        # 파일 업로드
        uploaded_files = st.file_uploader(
            "분석에 참고할 PDF 파일을 업로드하세요.",
            type="pdf",
            accept_multiple_files=True,
            key=f"uploader_{StateManager.get_uploader_key()}"
        )
        
        if uploaded_files:
            file_added = False
            for uploaded_file in uploaded_files:
                file_path = os.path.join(Config.DATA_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_added = True
            if file_added:
                st.success(f"{len(uploaded_files)}개의 파일이 추가되었습니다. RAG 파이프라인을 업데이트합니다.")
                # 업로더 위젯 상태를 초기화하기 위해 키를 변경 후 재실행
                StateManager.increment_uploader_key()
                st.cache_resource.clear()
                st.rerun()
        
        st.divider()
        
        # 현재 참고 중인 자료
        st.subheader("현재 참고 중인 자료")
        pdf_files_in_data = glob.glob(os.path.join(Config.DATA_DIR, "*.pdf"))
        if pdf_files_in_data:
            for f in pdf_files_in_data:
                st.info(f"📄 {os.path.basename(f)}")
        else:
            st.info("업로드된 파일이 없습니다. 기본 데이터로 분석합니다.")
        
        st.divider()
        
        # 분석 로그
        st.subheader("📊 분석 로그")
        
        # 로그 설정
        col1, col2 = st.columns(2)
        with col1:
            log_count = st.selectbox("로그 개수", [5, 10, 15, 20], index=1)
        with col2:
            if st.button("🗑️ 로그 클리어"):
                logger.clear_logs()
                st.rerun()
        
        # 로그 표시 영역
        recent_logs = logger.get_recent_logs(log_count)
        if recent_logs:
            # 로그를 역순으로 표시 (최신 로그가 위에)
            for log in reversed(recent_logs):
                # 로그 레벨에 따른 색상 구분
                if "❌" in log or "🚨" in log:
                    st.error(log, icon="❌")
                elif "⚠️" in log:
                    st.warning(log, icon="⚠️")
                elif "ℹ️" in log:
                    st.info(log, icon="ℹ️")
                else:
                    st.text(log)
        else:
            st.info("아직 로그가 없습니다. 분석을 시작하면 로그가 표시됩니다.")
        
        st.divider()
        
        # 사용 팁
        st.subheader("💡 사용 팁")
        
        st.info("""
        **효율적인 사용법:**
        - 📥 내보내기: 하단 버튼에서 대화를 파일로 저장
        - 📊 로그: 실시간 분석 과정을 확인
        - 🌐 웹검색: 최신 정보 수집 활성화/비활성화
        - 🔄 초기화: 새로운 대화 시작
        """)
        
        return uploaded_files 
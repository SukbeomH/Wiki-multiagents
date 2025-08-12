#!/usr/bin/env python3
"""
Task 11.4 E2E 테스트 스크립트
실제 Streamlit 앱에서 멀티 에이전트 라우팅 검증
"""

import requests
import time
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_streamlit_app():
    """Streamlit 앱의 기본 동작을 테스트합니다."""
    
    base_url = "http://localhost:8501"
    
    print("=== Task 11.4 E2E 테스트 시작 ===")
    
    # 1. 앱 접속 테스트
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("✅ Streamlit 앱 접속 성공")
        else:
            print(f"❌ 앱 접속 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 앱 접속 오류: {e}")
        return False
    
    # 2. 앱 상태 확인
    try:
        # Streamlit의 상태 엔드포인트 확인
        status_response = requests.get(f"{base_url}/_stcore/health", timeout=5)
        if status_response.status_code == 200:
            print("✅ 앱 상태 정상")
        else:
            print(f"⚠️ 앱 상태 확인 실패: {status_response.status_code}")
    except Exception as e:
        print(f"⚠️ 상태 확인 오류: {e}")
    
    print("\n=== 테스트 시나리오 안내 ===")
    print("다음 단계를 수동으로 진행해주세요:")
    print("1. 브라우저에서 http://localhost:8501 접속")
    print("2. 테스트 질문 입력: '최근 기준금리 동결의 영향 분석'")
    print("3. 다음 사항들을 확인:")
    print("   - st.status 단계별 레이블 갱신")
    print("   - 최종 응답이 채팅에 표시되는지")
    print("   - 터미널에서 로그 확인")
    
    return True

def check_logs():
    """로그 파일이나 터미널 출력을 확인하는 함수"""
    print("\n=== 로그 확인 가이드 ===")
    print("Streamlit 앱을 실행한 터미널에서 다음 로그 패턴을 확인하세요:")
    print("- [run] supervisor 단계")
    print("- [run] researcher 단계") 
    print("- [run] analyst 단계")
    print("- [run] 최종 응답 준비 완료")
    print("- [run] 최종 응답 길이=...")

def main():
    """메인 테스트 함수"""
    print("Task 11.4 - 질의 처리 및 멀티 에이전트 라우팅 검증")
    print("=" * 60)
    
    # 기본 연결 테스트
    if test_streamlit_app():
        check_logs()
        
        print("\n=== 수동 테스트 체크리스트 ===")
        print("다음 항목들을 확인하고 체크해주세요:")
        print()
        print("□ 1. 앱 초기화 완료 (RAG 리트리버 준비 완료)")
        print("□ 2. 질문 입력 후 상태 표시 업데이트")
        print("□ 3. Supervisor → Researcher → Analyst 순서로 진행")
        print("□ 4. 최종 응답이 채팅에 정상 표시")
        print("□ 5. 응답 길이가 0이 아님")
        print("□ 6. 터미널 로그에서 각 단계별 메시지 확인")
        print()
        print("모든 항목이 체크되면 Task 11.4가 성공적으로 완료됩니다!")
    else:
        print("❌ 기본 테스트 실패 - 앱 상태를 확인해주세요")

if __name__ == "__main__":
    main() 
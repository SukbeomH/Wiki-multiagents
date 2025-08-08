#!/usr/bin/env python3
"""
AI Knowledge Graph System - 통합 실행 스크립트

Streamlit UI와 FastAPI 서버를 한 번에 실행합니다.
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path
import requests
import psutil

class SystemManager:
    """시스템 관리자 클래스"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.processes = []
        self.running = True
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n🛑 종료 신호 수신 (시그널: {signum})")
        self.stop_all_services()
        sys.exit(0)
    
    def check_port_available(self, port):
        """포트 사용 가능 여부 확인"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def kill_process_on_port(self, port):
        """특정 포트에서 실행 중인 프로세스 종료"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    for conn in proc.info['connections']:
                        if conn.laddr.port == port:
                            print(f"🔪 포트 {port}에서 실행 중인 프로세스 종료: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.terminate()
                            proc.wait(timeout=5)
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    continue
        except Exception as e:
            print(f"⚠️ 프로세스 종료 중 오류: {e}")
        return False
    
    def start_fastapi_server(self):
        """FastAPI 서버 시작"""
        print("🚀 FastAPI 서버 시작 중...")
        
        # 포트 8000 확인 및 정리
        if not self.check_port_available(8000):
            print("⚠️ 포트 8000이 사용 중입니다. 기존 프로세스를 종료합니다.")
            self.kill_process_on_port(8000)
            time.sleep(2)
        
        try:
            # FastAPI 서버 실행
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                "src.api.main:app", 
                "--reload", 
                "--port", "8000", 
                "--host", "localhost"
            ], cwd=self.project_root)
            
            self.processes.append(("FastAPI", process))
            print(f"✅ FastAPI 서버 시작됨 (PID: {process.pid})")
            
            # 서버 시작 대기
            time.sleep(3)
            
            # 헬스 체크
            self.wait_for_api_health()
            
        except Exception as e:
            print(f"❌ FastAPI 서버 시작 실패: {e}")
            return False
        
        return True
    
    def start_streamlit_ui(self):
        """Streamlit UI 시작"""
        print("🚀 Streamlit UI 시작 중...")
        
        # 포트 8501 확인 및 정리
        if not self.check_port_available(8501):
            print("⚠️ 포트 8501이 사용 중입니다. 기존 프로세스를 종료합니다.")
            self.kill_process_on_port(8501)
            time.sleep(2)
        
        try:
            # Streamlit UI 실행
            process = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", 
                "src/ui/main.py",
                "--server.port", "8501",
                "--server.address", "localhost",
                "--browser.gatherUsageStats", "false"
            ], cwd=self.project_root)
            
            self.processes.append(("Streamlit", process))
            print(f"✅ Streamlit UI 시작됨 (PID: {process.pid})")
            
            # UI 시작 대기
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Streamlit UI 시작 실패: {e}")
            return False
        
        return True
    
    def wait_for_api_health(self, max_retries=10):
        """API 헬스 체크 대기"""
        print("🔍 API 서버 헬스 체크 중...")
        
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
                if response.status_code == 200:
                    print("✅ API 서버 정상 동작 확인")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(f"⏳ API 서버 대기 중... ({i+1}/{max_retries})")
            time.sleep(2)
        
        print("⚠️ API 서버 헬스 체크 실패")
        return False
    
    def monitor_processes(self):
        """프로세스 모니터링"""
        while self.running:
            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"⚠️ {name} 프로세스가 종료되었습니다. (종료 코드: {process.returncode})")
                    self.running = False
                    break
            time.sleep(5)
    
    def stop_all_services(self):
        """모든 서비스 종료"""
        print("\n🛑 모든 서비스를 종료합니다...")
        
        for name, process in self.processes:
            try:
                print(f"🔪 {name} 프로세스 종료 중... (PID: {process.pid})")
                process.terminate()
                process.wait(timeout=10)
                print(f"✅ {name} 프로세스 종료 완료")
            except subprocess.TimeoutExpired:
                print(f"⚠️ {name} 프로세스 강제 종료")
                process.kill()
            except Exception as e:
                print(f"❌ {name} 프로세스 종료 실패: {e}")
        
        self.processes.clear()
        print("👋 모든 서비스가 종료되었습니다.")
    
    def print_status(self):
        """시스템 상태 출력"""
        print("\n" + "="*60)
        print("🧠 AI Knowledge Graph System - 실행 상태")
        print("="*60)
        
        # 포트 상태 확인
        api_status = "🟢 실행 중" if self.check_port_available(8000) == False else "🔴 중지됨"
        ui_status = "🟢 실행 중" if self.check_port_available(8501) == False else "🔴 중지됨"
        
        print(f"📡 FastAPI 서버 (포트 8000): {api_status}")
        print(f"🖥️  Streamlit UI (포트 8501): {ui_status}")
        
        print("\n🌐 접속 정보:")
        print("   • UI: http://localhost:8501")
        print("   • API: http://localhost:8000")
        print("   • API 문서: http://localhost:8000/docs")
        print("   • Health Check: http://localhost:8000/api/v1/health")
        
        print("\n📋 사용 방법:")
        print("   1. 브라우저에서 http://localhost:8501 접속")
        print("   2. 사이드바에 키워드 입력 (예: '인공지능', '머신러닝')")
        print("   3. '🔍 검색 시작' 버튼 클릭")
        print("   4. 지식 그래프 및 위키 문서 확인")
        
        print("\n⏹️  종료: Ctrl+C")
        print("="*60)
    
    def run(self):
        """시스템 실행"""
        print("🧠 AI Knowledge Graph System 시작 중...")
        print(f"📁 프로젝트 경로: {self.project_root}")
        print("-" * 60)
        
        # 가상환경 확인
        if not os.path.exists(self.project_root / "venv"):
            print("❌ 가상환경을 찾을 수 없습니다. 'venv' 디렉토리가 필요합니다.")
            return False
        
        # FastAPI 서버 시작
        if not self.start_fastapi_server():
            return False
        
        # Streamlit UI 시작
        if not self.start_streamlit_ui():
            return False
        
        # 상태 출력
        self.print_status()
        
        # 모니터링 시작
        monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
        monitor_thread.start()
        
        try:
            # 메인 루프
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의해 종료 요청됨")
        finally:
            self.stop_all_services()
        
        return True


def main():
    """메인 함수"""
    manager = SystemManager()
    success = manager.run()
    
    if success:
        print("🎉 시스템이 정상적으로 종료되었습니다.")
    else:
        print("❌ 시스템 실행 중 오류가 발생했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main() 
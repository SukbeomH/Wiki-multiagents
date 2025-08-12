#!/usr/bin/env python3
"""
스트리밍 로직 테스트 스크립트
Task 11.4 검증을 위한 테스트
"""

def test_streaming_logic():
    """스트리밍 로직을 시뮬레이션하여 테스트합니다."""
    
    # 시뮬레이션된 chunk 데이터들
    test_chunks = [
        # 1. Supervisor 시작
        {
            "supervisor": {
                "messages": [
                    type('MockMessage', (), {'content': 'ROUTE: researcher'})()
                ]
            }
        },
        # 2. Researcher 실행
        {
            "researcher": {
                "messages": [
                    type('MockMessage', (), {'content': '경제 데이터를 수집했습니다.'})()
                ]
            }
        },
        # 3. Analyst 실행 (최종 응답)
        {
            "analyst": {
                "messages": [
                    type('MockMessage', (), {'content': '분석 결과: 기준금리 동결의 영향은 다음과 같습니다...'})()
                ]
            }
        },
        # 4. 전체 메시지 스트림
        {
            "messages": [
                type('MockMessage', (), {'content': 'Final Answer: 분석이 완료되었습니다.', 'name': 'supervisor'})()
            ]
        }
    ]
    
    # 스트리밍 로직 시뮬레이션
    final_response = ""
    accumulated_messages = []
    
    print("=== 스트리밍 로직 테스트 시작 ===")
    
    for i, chunk in enumerate(test_chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Chunk keys: {list(chunk.keys())}")
        
        # Supervisor 단계 처리
        if "supervisor" in chunk:
            print("🧠 Supervisor 단계 처리")
            if supervisor_messages := chunk["supervisor"].get("messages"):
                last_supervisor_msg = supervisor_messages[-1]
                content = getattr(last_supervisor_msg, "content", "").strip()
                if content.startswith("Final Answer:"):
                    final_response = content.replace("Final Answer:", "").strip()
                    print(f"✅ Supervisor Final Answer 수집: {final_response[:50]}...")
                elif content:
                    accumulated_messages.append(content)
                    print(f"📝 Supervisor 메시지 누적: {content[:50]}...")
        
        # Researcher 단계 처리
        if "researcher" in chunk:
            print("🔍 Researcher 단계 처리")
            if researcher_messages := chunk["researcher"].get("messages"):
                content = getattr(researcher_messages[-1], "content", "").strip()
                if content:
                    accumulated_messages.append(content)
                    print(f"📝 Researcher 메시지 누적: {content[:50]}...")
        
        # Analyst 단계 처리
        if "analyst" in chunk:
            print("✍️ Analyst 단계 처리")
            if analyst_messages := chunk["analyst"].get("messages"):
                final_msg = analyst_messages[-1]
                content = getattr(final_msg, "content", "").strip()
                if content:
                    final_response = content
                    accumulated_messages.append(content)
                    print(f"✅ Analyst 최종 응답 수집: {final_response[:50]}...")
        
        # 전체 메시지 스트림 처리
        if messages := chunk.get("messages"):
            print("📨 전체 메시지 스트림 처리")
            last = messages[-1]
            last_content = getattr(last, "content", "").strip()
            last_name = getattr(last, "name", "")
            
            if last_content.startswith("Final Answer:"):
                cleaned = last_content.replace("Final Answer:", "").strip()
                if not cleaned.upper().startswith("ROUTE:"):
                    final_response = cleaned
                    print(f"✅ 전체 스트림에서 Final Answer 수집: {final_response[:50]}...")
            
            elif last_name == "analyst" and last_content:
                if not final_response:
                    final_response = last_content
                    print(f"✅ 전체 스트림에서 Analyst 응답 수집: {final_response[:50]}...")
                accumulated_messages.append(last_content)
    
    # 최종 응답 폴백 처리
    if not final_response and accumulated_messages:
        final_response = accumulated_messages[-1]
        print(f"🔄 폴백: 누적 메시지에서 최종 응답 수집: {final_response[:50]}...")
    
    if not final_response:
        final_response = "분석이 완료되었으나 응답을 생성하지 못했습니다."
        print("⚠️ 최종 응답이 비어있음 - 기본 메시지 사용")
    
    print(f"\n=== 최종 결과 ===")
    print(f"최종 응답 길이: {len(final_response)}")
    print(f"최종 응답: {final_response}")
    print(f"누적 메시지 수: {len(accumulated_messages)}")
    
    return final_response

if __name__ == "__main__":
    test_streaming_logic() 
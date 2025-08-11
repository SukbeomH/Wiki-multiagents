---
title: Research Session
query: "LangGraph Python에서 OpenAI/Azure Chat Completions의 tool_calls 처리 베스트 프랙티스와 에러 해결법을 조사하라.
- 핵심 포인트: "An assistant message with 'tool_calls' must be followed by tool messages ..." 400 오류 원인과 해결
- Worker 노드에서 ToolMessage(tool_call_id 매칭) 반환 규칙, 여러 tool_calls 동시 처리, 잘못된 tool_call 소비 방지(노드별 필터링)
- create_react_agent 사용 시 agent_scratchpad 타입 요구사항과 올바른 Prompt 구성(MessagesPlaceholder)
- LangGraph Python에서 ToolNode/StateGraph를 활용한 권장 루프(모델 호출→툴 실행→ToolMessage 추가→모델 재호출)
- Azure OpenAI 환경에서의 차이점(파라미터, 응답 포맷)과 주의사항
- MultiQueryRetriever 초기화/캐시 베스트 프랙티스(성능/중복 계산 방지)
- 예시 코드 및 공식 문서 링크 포함"
date: 8/11/2025
time: 3:23:15 PM
timestamp: 2025-08-11T06:23:15.435Z
exchanges: 1
---

# Research Session

## Initial Query

**Question:** LangGraph Python에서 OpenAI/Azure Chat Completions의 tool_calls 처리 베스트 프랙티스와 에러 해결법을 조사하라.
- 핵심 포인트: "An assistant message with 'tool_calls' must be followed by tool messages ..." 400 오류 원인과 해결
- Worker 노드에서 ToolMessage(tool_call_id 매칭) 반환 규칙, 여러 tool_calls 동시 처리, 잘못된 tool_call 소비 방지(노드별 필터링)
- create_react_agent 사용 시 agent_scratchpad 타입 요구사항과 올바른 Prompt 구성(MessagesPlaceholder)
- LangGraph Python에서 ToolNode/StateGraph를 활용한 권장 루프(모델 호출→툴 실행→ToolMessage 추가→모델 재호출)
- Azure OpenAI 환경에서의 차이점(파라미터, 응답 포맷)과 주의사항
- MultiQueryRetriever 초기화/캐시 베스트 프랙티스(성능/중복 계산 방지)
- 예시 코드 및 공식 문서 링크 포함

**Response:**

LangGraph Python 환경에서 OpenAI/Azure Chat Completions의 **tool_calls 처리 베스트 프랙티스**와 관련된 주요 이슈(특히 `"An assistant message with 'tool_calls' must be followed by tool messages ..."` 400 오류 원인 및 해결법)를 중심으로, Worker 노드의 ToolMessage 반환 규칙, 다중 tool_calls 동시 처리, agent_scratchpad 요구사항, StateGraph 기반 권장 루프, Azure OpenAI 환경 차이점, MultiQueryRetriever 캐시 최적화까지 상세히 정리합니다.

---

## 1. `"An assistant message with 'tool_calls' must be followed by tool messages ..."` 400 오류 원인과 해결법

- **원인**: OpenAI/Azure Chat Completions API에서 `tool_calls`가 포함된 assistant 메시지 뒤에는 반드시 그에 대응하는 `tool messages`가 순서대로 따라와야 합니다. 즉, assistant가 tool 호출을 지시하면, 클라이언트(워크플로우)에서 해당 tool을 실행하고, 그 결과를 `ToolMessage` 형태로 모델에 다시 전달해야 합니다. 이 순서가 깨지거나 누락되면 400 오류가 발생합니다[1][3].

- **해결법**:
  - assistant 메시지에 `tool_calls`가 있으면, 반드시 **모든 tool_call에 대해 대응하는 ToolMessage를 반환**해야 합니다.
  - tool_call ID와 ToolMessage의 `tool_call_id`가 정확히 매칭되어야 하며, 누락 없이 모두 처리되어야 합니다.
  - tool_call이 여러 개일 경우, 각각을 순서대로 처리하고 ToolMessage 리스트로 반환해야 합니다.
  - 메시지 순서가 올바른지, 즉 assistant 메시지 → tool 실행 결과 ToolMessage → 다시 assistant 메시지 순으로 루프가 유지되는지 검증해야 합니다.
  - LangGraph의 `agent_node` 구현 예시처럼, tool_call 필터링 후 tool 호출 결과를 ToolMessage 리스트로 반환하는 구조를 반드시 지켜야 합니다.

---

## 2. Worker 노드에서 ToolMessage(tool_call_id 매칭) 반환 규칙 및 다중 tool_calls 동시 처리

- Worker 노드는 `last_message.tool_calls` 리스트를 순회하며, **자신이 처리할 tool_call만 필터링**(예: 노드 이름 포함 여부로 필터링)하여 처리합니다.

- 각 tool_call에 대해:
  - tool_call의 `id`를 `ToolMessage`의 `tool_call_id`에 정확히 매핑해야 합니다.
  - tool_call 인자(`args`)를 적절히 파싱하여 tool 함수에 전달합니다.
  - tool 실행 결과를 `ToolMessage(content=결과, tool_call_id=tool_call.id)` 형태로 반환합니다.

- 다중 tool_calls가 있을 경우, 모든 해당 tool_call에 대해 ToolMessage를 생성하여 **리스트로 반환**해야 하며, 누락 시 400 오류 발생 가능성이 큽니다.

- 노드별 필터링은 tool_call 이름에 노드 이름이 포함되는 규칙을 활용하는 것이 실용적이며, 이를 통해 **잘못된 tool_call 소비 방지**가 가능합니다.

- 예시 코드 (app.py 내 `agent_node` 함수 참고):

```python
if hasattr(last_message, "tool_calls") and last_message.tool_calls:
    responses = []
    for tool_call in last_message.tool_calls:
        tool_name = (tool_call.get('name') or '').lower()
        if name not in tool_name:
            continue  # 다른 노드용 tool_call은 건너뜀
        # tool_call args 파싱
        tool_args = tool_call.get('args', {})
        worker_input = tool_args.get('input') or tool_args.get('query') or next(iter(tool_args.values()), "")
        # tool 호출
        invoke_result = agent.invoke({"input": worker_input, "agent_scratchpad": []})
        result_text = invoke_result.get("output", "")
        responses.append(ToolMessage(content=result_text, tool_call_id=tool_call.get('id')))
    return {"messages": responses}
```

---

## 3. `create_react_agent` 사용 시 `agent_scratchpad` 타입 요구사항과 올바른 Prompt 구성 (MessagesPlaceholder)

- `create_react_agent`는 내부적으로 **agent_scratchpad**라는 변수에 이전 tool 호출 기록(메시지 리스트)을 받습니다. 이 값은 반드시 **빈 리스트([]) 또는 메시지 리스트 형태**여야 하며, 문자열이나 None을 넘기면 오류가 발생할 수 있습니다.

- Prompt 구성 시 `MessagesPlaceholder(variable_name="agent_scratchpad")`를 사용하여, agent가 tool 호출 히스토리를 관리하도록 해야 합니다.

- Prompt 예시:

```python
prompt = ChatPromptTemplate.from_messages([    ("system", "{system_prompt}\n\n사용 가능한 도구:\n{tools}\n\n도구 이름 목록: {tool_names}"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
]).partial(system_prompt=system_prompt, tools=tools_desc, tool_names=tool_names)
```

- 호출 시 `agent.invoke({"input": user_input, "agent_scratchpad": []})` 형태로 빈 리스트를 넘겨 초기화하는 것이 안전합니다.

---

## 4. LangGraph Python에서 ToolNode/StateGraph를 활용한 권장 루프

- LangGraph의 StateGraph를 활용해 **모델 호출 → tool_calls 감지 → ToolNode(툴 실행) → ToolMessage 추가 → 모델 재호출**의 루프를 구성하는 것이 권장됩니다.

- 대표적인 패턴:

  1. **모델 호출 노드**: 사용자 메시지 또는 이전 상태 메시지를 모델에 전달하여 응답을 받음. 응답에 `tool_calls`가 있으면 다음 노드로 이동.

  2. **ToolNode**: `tool_calls`를 받아서 실제 도구를 실행하고, 결과를 `ToolMessage`로 반환.

  3. **모델 호출 노드 재진입**: ToolMessage를 포함한 메시지 상태로 다시 모델 호출.

- 이 루프를 통해 모델과 도구 간 상호작용을 자연스럽게 처리할 수 있습니다.

- LangGraph 공식 예시:

```python
builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_node("tools", tool_node)
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", should_continue, ["tools", END])
builder.add_edge("tools", "call_model")
graph = builder.compile()
```

- 위 구조는 tool_calls가 있으면 tool_node로 이동해 도구 실행 후 다시 모델 호출로 돌아오는 순환 구조입니다[2].

---

## 5. Azure OpenAI 환경에서의 차이점과 주의사항

- **파라미터 차이**:
  - Azure OpenAI는 `azure_deployment`, `azure_endpoint`, `api_key`, `api_version` 등의 파라미터를 요구하며, OpenAI 공식 API와 다르게 설정해야 합니다.
  - `api_version`은 `"2024-02-01"` 등 최신 버전을 사용해야 하며, 버전 미스매치 시 오류 발생 가능.

- **응답 포맷**:
  - Azure OpenAI Chat Completions는 tool_calls 포함 메시지 구조가 OpenAI와 유사하나, 일부 필드명이나 포맷이 다를 수 있어 LangChain/AzureChatOpenAI 래퍼를 반드시 사용해야 합니다.
  - tool_calls가 포함된 assistant 메시지 뒤에 반드시 tool message가 와야 하는 규칙은 동일.

- **주의사항**:
  - Azure 환경에서는 tool_calls가 포함된 메시지를 받았을 때, 반드시 tool 실행 후 ToolMessage를 포함해 재호출하는 루프를 엄격히 지켜야 400 오류를 방지할 수 있습니다.
  - Azure OpenAI의 rate limit, timeout 정책도 고려해야 하며, tool 호출 시 과도한 동시성은 피하는 것이 안정적입니다.

- LangChain AzureChatOpenAI 초기화 예시:

```python
llm = AzureChatOpenAI(
    azure_deployment=deployment_name,
    api_version="2024-02-01",
    azure_endpoint=endpoint,
    api_key=api_key,
    temperature=0,
)
```

---

## 6. MultiQueryRetriever 초기화 및 캐시 베스트 프랙티스

- MultiQueryRetriever는 여러 쿼리를 병렬로 처리해 검색 정확도를 높이는 리트리버입니다.

- 초기화 시, **임베딩 모델과 벡터스토어가 완성된 후에 한 번만 생성**하고, 이후에는 캐시(`@st.cache_resource` 등)를 활용해 중복 계산을 방지해야 합니다.

- 캐시 키는 다음 요소들을 포함하는 것이 좋습니다:
  - PDF 파일명 + 수정시간(mtime) 해시
  - 모델 버전 및 파라미터
  - 기타 환경 변수

- 예시 캐시 키 생성:

```python
import hashlib

def _file_sig(path: str) -> str:
    try:
        return f"{os.path.basename(path)}:{int(os.path.getmtime(path))}"
    except Exception:
        return os.path.basename(path)

key_src = APP_GRAPH_VERSION + "|" + ",".join(sorted([_file_sig(p) for p in pdf_files]))
cache_key = hashlib.sha256(key_src.encode()).hexdigest()
```

- 이렇게 하면 PDF가 변경되거나 추가될 때만 리트리버가 재생성되어 성능과 일관성을 유지할 수 있습니다.

---

## 7. 예시 코드 및 공식 문서 링크

- LangChain 공식 Tool Calling 문서: https://python.langchain.com/docs/concepts/tool_calling/[1]

- LangChain Tool Calling How-To: https://python.langchain.com/docs/how_to/function_calling/[3]

- LangGraph Tool Calling 예시: https://langchain-ai.github.io/langgraph/how-tos/tool-calling/[2]

- LangGraph Python 예제 및 StateGraph 활용: https://realpython.com/langgraph-python/[4]

- 프로젝트 내 `app.py` 주요 코드 참고:
  - `agent_node` 함수: tool_calls 필터링 및 ToolMessage 반환
  - `create_agent` 함수: `create_react_agent`와 `MessagesPlaceholder` 사용
  - `create_graph` 함수: StateGraph에 supervisor, researcher, analyst 노드 추가 및 tool_calls 기반 조건부 엣지 설정
  - `build_rag_pipeline` 함수: MultiQueryRetriever 캐시 처리

---

## 8. 추가 권장 사항 및 주의점

- **tool_calls가 없는 메시지 처리**: tool_calls가 없으면 빈 메시지 리스트를 반환하거나 supervisor로 복귀하도록 하여 루프가 멈추지 않도록 해야 합니다.

- **에러 처리**: Worker 노드에서 예외 발생 시, `HumanMessage`로 에러 메시지를 반환하여 Supervisor가 재할당 또는 종료 판단할 수 있게 구현하는 것이 안정적입니다.

- **멀티 에이전트 동시 tool_calls 처리**: Supervisor가 여러 tool_calls를 동시에 생성할 경우, Worker 노드는 자신의 이름이 포함된 tool_call만 처리하고 나머지는 무시하여 충돌 방지.

- **agent_scratchpad 관리**: tool 호출 히스토리를 빈 리스트로 초기화하고, 필요 시 이전 호출 기록을 누적하여 전달하는 방식으로 agent 상태를 관리.

- **Azure OpenAI API 버전 관리**: 최신 API 버전을 사용하고, LangChain/AzureChatOpenAI 라이브러리 버전도 최신으로 유지해야 호환성 문제를 줄일 수 있습니다.

---

이상은 LangGraph Python에서 OpenAI/Azure Chat Completions의 tool_calls 처리 관련 핵심 베스트 프랙티스와 400 오류 해결법, Worker 노드 처리 규칙, agent_scratchpad 요구사항, StateGraph 루프 구성, Azure 환경 특성, MultiQueryRetriever 캐시 최적화, 그리고 관련 예시 코드 및 공식 문서 링크를 종합한 상세 가이드입니다. 프로젝트 내 `app.py` 코드 구조와도 일치하며, 이를 참고해 안정적인 멀티 에이전트 tool_calls 워크플로우를 구현할 수 있습니다.


---

*Generated by Task Master Research Command*  
*Timestamp: 2025-08-11T06:23:15.435Z*

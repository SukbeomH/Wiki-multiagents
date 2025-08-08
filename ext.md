다음 예제는 **spaCy**로 한국어 텍스트에서 먼저 엔티티를 뽑고, **datawhales/korre**로 관계를 추출한 뒤, **LangChain/LangGraph** 에이전트 워크플로우를 통해 처리하고, 마지막으로 **RDFLib + SQLiteStore** 에 영구 저장하는 전체 파이프라인입니다.

---

## 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv && source venv/bin/activate

# 필수 패키지 설치
pip install spacy langchain langgraph rdflib korre

# spaCy 한국어 모델 설치
python -m spacy download ko_core_news_sm
```

---

## 2. spaCy NER 툴 정의

```python
import spacy
from langchain_core.tools import tool

# 한국어 모델 로드
nlp_ko = spacy.load("ko_core_news_sm")

@tool("spacy_ner", "한국어 텍스트에서 기본 엔티티(인물·장소·조직) 추출")
def spacy_ner(text: str) -> list[dict]:
    doc = nlp_ko(text)
    return [{"text": ent.text, "start": ent.start_char, "end": ent.end_char, "label": ent.label_}
            for ent in doc.ents]
```

---

## 3. KorRE 관계 추출 툴 정의

```python
from korre import KorRE
from langchain_core.tools import tool

# KorRE 인스턴스 생성 (모델 자동 로드) :contentReference[oaicite:0]{index=0}
korre = KorRE()

@tool("korre_re", "문장과 엔티티 위치를 받아 한국어 관계 추출")
def korre_re(text: str, idx1: list[int], idx2: list[int]) -> list[tuple[str,str,str]]:
    """
    Args:
        text (str): 원문
        idx1 (list[int]): 첫 번째 엔티티 [start, end]
        idx2 (list[int]): 두 번째 엔티티 [start, end]
    Returns:
        List of (주어, 목적어, 관계) triples
    """
    return korre.infer(text, idx1, idx2)
```

---

## 4. LangGraph 에이전트 및 StateGraph 구성

```python
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 상태 타입 정의
class KGState(TypedDict):
    messages: list[dict]

# 1) NER 에이전트
ner_agent = create_react_agent(
    model="openai:gpt-4",
    tools=[spacy_ner],
    prompt="한국어 문장에서 엔티티(text, start, end, label)를 추출하여 리스트로 반환하세요.",
    name="ner_agent",
)

# 2) 관계추출 에이전트
re_agent = create_react_agent(
    model="openai:gpt-4",
    tools=[korre_re],
    prompt=(
        "추출된 엔티티 리스트와 원문을 받아, "
        "각 엔티티 쌍의 위치 인덱스를 korre_re에 전달해 관계(triple)를 추출하세요."
    ),
    name="re_agent",
)

# 3) 그래프 빌드 (START → ner_agent → re_agent → END)
graph = (
    StateGraph(KGState)
    .add_node(ner_agent, destinations=("re_agent", END))
    .add_node(re_agent)
    .add_edge(START, "ner_agent")
    .add_edge("ner_agent", "re_agent")
    .add_edge("re_agent", END)
    .compile()
)
```

---

## 5. RDFLib + SQLiteStore 초기화

```python
from rdflib import Graph, Namespace, URIRef, RDF

# 1) Graph 열기 (SQLiteStore)
kg = Graph(store="SQLite")
kg.open("kg.db", create=True)

# 2) 네임스페이스 정의
EX = Namespace("http://example.org/")
```

---

## 6. 파이프라인 실행 및 트리플 적재

```python
# 예시 문장
text = "갤럭시 플립2는 삼성에서 만든 스마트폰이다."

# 1) LangGraph 실행
state = {"messages": [{"role": "user", "content": text}]}
for _ in graph.stream(state):
    pass  # 내부에서 spacy_ner, korre_re 호출

# 2) spaCy로 엔티티 직접 추출 (백업용)
entities = spacy_ner(text)
# korre.ner 로도 인덱스 뽑기 가능 :contentReference[oaicite:1]{index=1}
# entities = korre.ner(text)

# 3) 관계 추출: 문장만 입력해 모든 관계 추출 (korre.infer(text)) :contentReference[oaicite:2]{index=2}
relations = korre.infer(text)

# 4) RDF 트리플로 변환·추가
for ent in entities:
    uri = EX[ent["text"].replace(" ", "_")]
    kg.add((URIRef(uri), RDF.type, EX[ent["label"]]))

for subj, obj, pred in relations:
    subj_uri = EX[subj.replace(" ", "_")]
    obj_uri  = EX[obj.replace(" ", "_")]
    # predicate는 관계명을 그대로 사용
    kg.add((URIRef(subj_uri), EX[pred], URIRef(obj_uri)))

# 5) 저장 및 종료
kg.close()
```

---

## 7. SPARQL 예시 조회

```python
from rdflib.plugins.sparql import prepareQuery

kg = Graph(store="SQLite")
kg.open("kg.db", create=False)

q = prepareQuery("""
  SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
  }
""")
for s, p, o in kg.query(q):
    print(s, p, o)
kg.close()
```

---

이로써 **spaCy → datawhales/korre → LangChain/LangGraph** 를 거쳐 추출된 엔티티·관계를 **RDFLib+SQLite** 에 영구 저장하는 완전한 파이프라인이 구성됩니다.
— KorRE 설치 및 Quick Start ([GitHub][1])

[1]: https://github.com/datawhales/korre "GitHub - datawhales/korre: 한국어 관계 추출 모듈을 구현한 라이브러리입니다."

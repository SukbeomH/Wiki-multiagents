# 프롬프트 템플릿

이 디렉토리는 각 에이전트가 사용하는 AI 프롬프트 템플릿을 포함합니다.

## 구조

```
prompts/
├── research/           # Research Agent 프롬프트
├── extractor/         # Extractor Agent 프롬프트
├── retriever/         # Retriever Agent 프롬프트
├── wiki/              # Wiki Agent 프롬프트
├── graphviz/          # GraphViz Agent 프롬프트
├── supervisor/        # Supervisor Agent 프롬프트
├── feedback/          # Feedback Agent 프롬프트
└── shared/            # 공통 프롬프트
```

## 사용법

각 에이전트는 Jinja2 템플릿을 사용하여 동적으로 프롬프트를 생성합니다.

예시:
```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('prompts'))
template = env.get_template('extractor/entity_extraction.jinja2')
prompt = template.render(document=doc, context=context)
```
# UI 실행 가이드

- 환경 변수 설정(선택):
  - `API_BASE_URL` (기본값: `http://localhost:8000/api/v1`)

- API 서버 실행:
  - 가상환경 활성화 후
  - `uvicorn src.api.main:app --reload --port 8000`

- Streamlit UI 실행:
  - `streamlit run app/main.py`

- 확인 포인트:
  - 토론 시작 시 서버의 `/api/v1/workflow/debate/stream`가 정상 스트림 반환
  - "토론 이력" 탭에서 CRUD가 정상 동작 (`/api/v1/debates/`)

# PHASE_5_RESULT

Phase: 5 — Tool/API Hub + Mock API
완료일: 2026-06-09

---

## 완료된 작업

- [x] mock-api/main.py — 4개 Mock 엔드포인트 추가
- [x] backend/app/tools/__init__.py
- [x] backend/app/tools/tool_gateway.py — Tool 목록 조회 + httpx 호출
- [x] backend/app/schemas/tool.py — ToolResponse, ToolInvokeRequest/Response
- [x] backend/app/api/routes/tool.py — 2개 엔드포인트
- [x] backend/app/main.py — tool 라우터 include 추가

---

## Mock API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | /products | 대출 상품 목록 (product_type 필터 optional) |
| GET | /rates | 금리 정보 (product_id 필터 optional) |
| GET | /policies | 정책/약관 (policy_type 필터 optional) |
| GET | /documents/search | 필요서류 검색 (keyword 필터 optional) |

## Tool Hub 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | /api/v1/tools | 활성 tool 전체 목록 |
| POST | /api/v1/tools/invoke | api_id + params → Mock API 호출 후 응답 반환 |

---

## 핵심 설계 결정

- Tool = `api_catalog` 테이블 — 별도 테이블 없이 기존 모델 재사용
- Hub 오류 흡수: invoke 실패 시 예외 미전파, `status="error"` 반환 → Orchestrator fallback 가능
- async 호출: httpx.AsyncClient + FastAPI async 라우터로 네트워크 I/O 비차단 처리

---

## 완료 조건 확인

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed.run_seed

# Mock API 직접
curl http://localhost:8010/products
curl "http://localhost:8010/rates?product_id=P001"
curl http://localhost:8010/policies
curl "http://localhost:8010/documents/search?keyword=재직"

# Tool Hub
curl http://localhost:8000/api/v1/tools
curl -X POST http://localhost:8000/api/v1/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"api_id": "MOCK_PRODUCT_LOOKUP", "params": {}}'
curl -X POST http://localhost:8000/api/v1/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{"api_id": "MOCK_RATE_LOOKUP", "params": {"product_id": "P001"}}'
```

---

## 다음 Phase

Phase 6: Leader Agent / Orchestrator

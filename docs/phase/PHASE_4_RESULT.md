# PHASE_4_RESULT

Phase: 4 — Agent Registry + Agent Router
완료일: 2026-06-09

---

## 완료된 작업

- [x] backend/app/agents/__init__.py
- [x] backend/app/schemas/agent.py — AgentResponse, AgentDetailResponse, AgentRouteRequest/Response
- [x] backend/app/agents/agent_registry.py — 3개 서비스 함수
- [x] backend/app/api/routes/agent.py — 3개 엔드포인트
- [x] backend/app/main.py — agent 라우터 include 추가

---

## 엔드포인트 목록

| Method | Path | 설명 |
|---|---|---|
| GET | /api/v1/agents | 활성 agent 전체 목록 (LEADER_AGENT 포함) |
| GET | /api/v1/agents/{agent_id} | agent 상세 + 담당 concept_id 목록 |
| POST | /api/v1/agents/route | concept_id 배열 → 라우팅 계획 반환 |

---

## 라우팅 원칙

- LLM 임의 판단 없음 — `agent_concept_mapping` 테이블만 사용
- 동일 Agent가 여러 concept를 담당하면 하나의 `AgentRouteItem`으로 합산
- 매핑된 Agent 없는 concept는 `unrouted_concept_ids`에 포함 → Leader Agent가 결정

---

## 완료 조건 확인

```bash
docker compose up -d --build

curl http://localhost:8000/api/v1/agents
curl http://localhost:8000/api/v1/agents/RATE_AGENT
curl -X POST http://localhost:8000/api/v1/agents/route \
  -H "Content-Type: application/json" \
  -d '{"concept_ids": ["CONCEPT_INTEREST_RATE", "CONCEPT_LOAN_PRODUCT"]}'
```

예상 응답:
- `/agents` → 5개 agent 배열
- `/agents/RATE_AGENT` → concept_ids: ["CONCEPT_INTEREST_RATE", "CONCEPT_PREFERENTIAL_RATE"]
- `/agents/route` → routing: [RATE_AGENT, PRODUCT_AGENT], unrouted_concept_ids: []

---

## 다음 Phase

Phase 5: Tool/API Hub + Mock API

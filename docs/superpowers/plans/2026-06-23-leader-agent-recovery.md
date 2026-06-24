# Leader Agent Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `backend/app/agents/leader.py`의 현재 보수적 복구 상태를 원래 동작 수준으로 되돌리고, 이후 slimming/refactor를 다시 진행할 수 있는 안정된 기준선을 만든다.

**Architecture:** 먼저 API 레벨 골든/회귀 테스트로 현재 기대 동작을 고정한다. 그 다음 `leader.py`의 임시 단순화된 helper와 orchestration을 원래 책임 수준으로 단계 복구하고, 마지막에 서비스 분리 경계를 다시 맞춘다. 동작 복구와 구조 개선은 같은 단계에서 섞지 않는다.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Docker Compose, existing agent services, trace/evidence services

---

## File Structure

### Existing files to modify

- `backend/app/agents/leader.py`
  - 현재 임시 단순화된 helper와 orchestration을 원래 동작 수준으로 복구한다.
- `backend/tests/test_chat.py`
  - 실제 사용자 회귀 케이스와 대표 질의 회귀 테스트를 추가한다.
- `backend/tests/test_leader_golden.py`
  - leader 복구 기준 시나리오를 보강한다.

### Existing files to reference

- `backend/app/agents/rate_agent.py`
  - 신용등급/개인화 금리 질의가 어떤 API를 우선 타야 하는지 확인한다.
- `backend/app/agents/formatters/loan_formatter.py`
  - 개별 금리/상품/맞춤금리 응답 포맷 기대치를 확인한다.
- `backend/app/knowledge/concept_service.py`
  - concept 감지/alias 검색의 원래 동작을 확인한다.
- `backend/app/agents/services/concept_resolution_service.py`
  - 현재 분리된 concept resolution 구현을 검토한다.
- `backend/app/agents/services/routing_policy.py`
  - 현재 분리된 routing/rule 구현을 검토한다.
- `backend/app/agents/services/execution_planner.py`
  - 현재 분리된 planner 구현을 검토한다.
- `backend/app/agents/services/answer_composer.py`
  - 현재 분리된 answer composition 경계를 검토한다.
- `backend/app/agents/clarification_service.py`
  - clarification flow 원래 책임을 확인한다.

### New files to create

- `docs/leader-recovery-notes.md`
  - 복구 중 확인한 회귀 원인과 후속 slimming 주의사항을 기록한다.

---

### Task 1: Recovery Baseline Tests

**Files:**
- Modify: `backend/tests/test_chat.py`
- Modify: `backend/tests/test_leader_golden.py`

- [x] **Step 1: 신용등급 회귀 테스트 유지**

확인 기준:

```python
def test_chat_credit_grade_query_prefers_personalized_rate_output(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "내 신용등급이 어떠해?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    api_ids = [r["api_id"] for r in body["results"]]
    assert "MOCK_PERSONALIZED_RATE_LOOKUP" in api_ids
    assert "신용등급" in body["answer"]
    assert "대출 상품" not in body["answer"]
```

- [x] **Step 2: 일반 금리 질의 회귀 테스트 추가**

```python
def test_chat_rate_query_does_not_return_product_section(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 얼마야?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "MOCK_RATE_LOOKUP" in [r["api_id"] for r in body["results"]]
    assert "금리" in body["answer"]
```

- [x] **Step 3: 상품 질의 회귀 테스트 추가**

```python
def test_chat_product_query_keeps_product_section(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "대출 상품 종류 알려줘"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "MOCK_PRODUCT_LOOKUP" in [r["api_id"] for r in body["results"]]
    assert "대출 상품" in body["answer"]
```

- [x] **Step 4: failing test 실행으로 기준선 확인**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py -k "credit_grade_query_prefers_personalized_rate_output or rate_query_does_not_return_product_section or product_query_keeps_product_section" -v
```

Expected:

```text
현재 복구 전 상태에서 일부 FAIL 가능. 실패 메시지를 leader 복구 기준으로 사용.
```

---

### Task 2: Restore Question-Focused Filtering

**Files:**
- Modify: `backend/app/agents/leader.py`
- Reference: `backend/app/seed/intent_synonyms_seed.py`
- Test: `backend/tests/test_chat.py`

- [x] **Step 1: `_load_focus_keywords` / `_load_api_concept_map` 복구**

복구 대상 함수:

```python
def _load_focus_keywords(db) -> dict[str, list[str]]: ...
def _load_api_concept_map(db) -> dict[str, list[str]]: ...
def clear_focus_keywords_cache() -> None: ...
```

- [x] **Step 2: `_detect_concepts_via_synonyms` 복구**

```python
def _detect_concepts_via_synonyms(message: str, db) -> list[str]:
    focus_keywords = _load_focus_keywords(db)
    api_concept_map = _load_api_concept_map(db)
    msg_lower = message.lower()
    ...
```

- [x] **Step 3: `_filter_results_by_question` 복구**

복구 포인트:

```python
if "MOCK_PERSONALIZED_RATE_LOOKUP" in matched_apis:
    matched_apis.discard("MOCK_RATE_LOOKUP")
    matched_apis.discard("MOCK_PRODUCT_LOOKUP")
```

- [x] **Step 4: targeted test 실행**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py -k credit_grade_query_prefers_personalized_rate_output -v
```

Expected:

```text
PASS
```

---

### Task 3: Restore Concept Detection and Expansion Fidelity

**Files:**
- Modify: `backend/app/agents/leader.py`
- Modify: `backend/app/agents/services/concept_resolution_service.py`
- Reference: `backend/app/knowledge/concept_service.py`
- Test: `backend/tests/test_leader_golden.py`

- [x] **Step 1: concept resolution 회귀 테스트 추가**

```python
def test_leader_golden_credit_grade_query_detects_rate_concept(client):
    body = _post_chat(client, "내 신용등급이 어떠해?")
    assert "CONCEPT_INTEREST_RATE" in body["plan"]["detected_concepts"]
```

- [x] **Step 2: `ConceptResolutionService.resolve()` 가 direct + keyword + synonym fallback + relation expansion 을 모두 유지하는지 확인**

검토 포인트:

```python
for concept in detect_concepts_in_message(...): ...
for kw in intent_keywords: ...
for concept_id in self._detect_concepts_via_synonyms(...): ...
all_concepts = self._expand_via_relations(...)
```

- [x] **Step 3: `leader.py` 가 더 이상 임시 fallback/stub 로직을 사용하지 않는지 확인**

확인 기준:

```python
resolved = self._concept_resolution_service.resolve(...)
detected = resolved.detected
all_concepts = resolved.all_concepts
detected_set = resolved.detected_set
```

- [x] **Step 4: 테스트 실행**

Run:

```bash
docker compose exec backend pytest tests/test_leader_golden.py -k credit_grade_query_detects_rate_concept -v
```

Expected:

```text
PASS
```

---

### Task 4: Restore Routing and Decision Fidelity

**Files:**
- Modify: `backend/app/agents/leader.py`
- Modify: `backend/app/agents/services/routing_policy.py`
- Reference: `backend/app/agents/agent_registry.py`
- Test: `backend/tests/test_chat.py`

- [x] **Step 1: rate routing 회귀 테스트 추가**

```python
def test_chat_credit_grade_query_routes_rate_agent(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "내 신용등급이 어떠해?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "RATE_AGENT" in body["plan"]["routed_agents"]
```

- [x] **Step 2: `RoutingPolicy.route()` 의 selected/rejected agent 계산이 기존 decision rule 기대와 맞는지 확인**

검토 포인트:

```python
route_result = route_by_concepts(db, all_concepts)
classified = self.classify_concepts(...)
triggered_rules, selected_agents_v2, rejected_agents_v2 = self.evaluate_decision_rules(...)
```

- [x] **Step 3: `leader.py` 에서 routing 결과를 덮어쓰거나 누락시키는 임시 조합이 없는지 확인**

- [x] **Step 4: 테스트 실행**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py -k credit_grade_query_routes_rate_agent -v
```

Expected:

```text
PASS
```

---

### Task 5: Restore Execution Planning and Tool Selection

**Files:**
- Modify: `backend/app/agents/leader.py`
- Modify: `backend/app/agents/services/execution_planner.py`
- Reference: `backend/app/knowledge/concept_service.py`
- Test: `backend/tests/test_chat.py`

- [x] **Step 1: personalized rate plan 회귀 테스트 추가**

```python
def test_chat_credit_grade_query_plan_includes_personalized_rate_lookup(client):
    resp = client.post(
        "/api/v1/ai/chat",
        json={"message": "내 신용등급이 어떠해?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    api_ids = [step["api_id"] for step in body["plan"]["steps"]]
    assert "MOCK_PERSONALIZED_RATE_LOOKUP" in api_ids
```

- [x] **Step 2: `ExecutionPlanner.build_steps()` 가 concept별 API priority 와 dedupe 를 유지하는지 확인**

- [x] **Step 3: `leader.py` 의 step 조합이 planner 결과를 우회하지 않는지 확인**

- [x] **Step 4: 테스트 실행**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py -k credit_grade_query_plan_includes_personalized_rate_lookup -v
```

Expected:

```text
PASS
```

---

### Task 6: Restore Clarification and Pending-State Handling

**Files:**
- Modify: `backend/app/agents/leader.py`
- Modify: `backend/app/agents/services/clarification_service_adapter.py`
- Reference: `backend/app/agents/clarification_service.py`
- Test: `backend/tests/test_leader_golden.py`

- [x] **Step 1: clarification 회귀 테스트 유지/보강**

```python
def test_leader_golden_clarification_query(client):
    body = _post_chat(client, "대출 신청하려면?")
    assert "needs_clarification" in body
```

- [x] **Step 2: `try_resolve()` 와 `leader.py` 의 pending merge 흐름이 원래 의미를 유지하는지 확인**

특히 확인할 것:

```python
if pending is None:
    message = snapshot.get("original_message", message) + " " + message
```

- [x] **Step 3: 테스트 실행**

Run:

```bash
docker compose exec backend pytest tests/test_leader_golden.py -k clarification -v
```

Expected:

```text
PASS
```

---

### Task 7: Restore Trace, Evidence, and Monitoring Coverage

**Files:**
- Modify: `backend/app/agents/leader.py`
- Reference: `backend/app/services/decision_trace_service.py`
- Reference: `backend/app/trace/evidence_service.py`
- Test: `backend/tests/test_chat.py`

- [x] **Step 1: trace/evidence 회귀 테스트 확인**

기존 테스트를 기준선으로 사용:

```python
def test_chat_trace_count(client): ...
def test_chat_evidence_count(client): ...
def test_chat_records_documented_trace_events(client, db): ...
```

- [x] **Step 2: `leader.py` 에서 임시 축약으로 빠진 trace/evidence 저장 흐름이 없는지 확인**

체크 포인트:

```python
save_decision_trace_core(...)
save_concept_detections(...)
save_agent_selection_rows(...)
save_tool_execution_rows(...)
save_reranking_trace(...)
save_final_answer_trace(...)
link_related_evidence(...)
```

- [x] **Step 3: 테스트 실행**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py -k "trace_count or evidence_count or records_documented_trace_events" -v
```

Expected:

```text
PASS
```

---

### Task 8: Full Regression and Recovery Notes

**Files:**
- Modify: `backend/tests/test_chat.py`
- Modify: `backend/tests/test_leader_golden.py`
- Create: `docs/leader-recovery-notes.md`

- [x] **Step 1: 핵심 leader 회귀 테스트 전체 실행**

Run:

```bash
docker compose exec backend pytest tests/test_chat.py tests/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [x] **Step 2: 복구 메모 작성**

`docs/leader-recovery-notes.md` 에 기록할 항목:

```text
1. 깨진 직접 원인
2. 임시 복구 중 축약되면 안 되는 helper 목록
3. slimming 재개 전 유지해야 할 골든 테스트 목록
4. 다음 refactor에서 먼저 분리할 책임과 나중에 분리할 책임
```

- [x] **Step 3: slimming 재개 조건 기록**

```text
1. test_chat.py 핵심 회귀 PASS
2. test_leader_golden.py PASS
3. 신용등급/금리/상품/서류/clarification 대표 질문 수동 확인
4. 그 다음에만 leader slimming 재시작
```

---

## Self-Review

### Spec coverage

- 현재 깨진 실제 사용자 케이스인 `내 신용등급이 어떠해?` 를 기준 회귀 테스트로 고정했다.
- leader 전체 복구를 concept, routing, plan, clarification, trace/evidence, answer composition으로 분해했다.
- 동작 복구 후에만 다시 slimming 으로 넘어가도록 순서를 명확히 분리했다.

### Placeholder scan

- 각 task 에 구체 파일 경로, 테스트 이름, 실행 명령을 넣었다.
- “적절히 처리” 같은 모호한 문구 대신 확인해야 할 함수와 기대 결과를 적었다.

### Type consistency

- `LeaderAgent`, `ConceptResolutionService`, `RoutingPolicy`, `ExecutionPlanner`, `ClarificationServiceAdapter`, `LeaderResult`, `ExecutionPlan`, `StepResult` 기준으로 일관되게 적었다.
- 회귀 테스트도 모두 `/api/v1/ai/chat` 응답 스키마 기준으로 맞췄다.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-leader-agent-recovery.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?


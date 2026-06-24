# Leader Agent Slimming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `backend/app/agents/leader.py`의 비대화 원인이 되는 판단, 요약, 분기 로직을 서비스로 분리해 `LeaderAgent`를 오케스트레이터 중심으로 축소한다.

**Architecture:** `LeaderAgent`는 요청 진입점과 전체 실행 순서만 관리하고, intent 분석, concept 해석, 라우팅 정책, 실행 계획, 응답 조합은 별도 서비스가 담당한다. 1차 리팩토링은 동작 변경 없이 책임만 이동하는 것을 목표로 한다.

**Tech Stack:** FastAPI, SQLAlchemy, existing agent services, existing AI gateway schemas, trace/evidence services

---

## File Structure

### Existing files to modify

- `backend/app/agents/leader.py`
  - 현재 비대한 오케스트레이션 + 판단 로직을 얇은 coordinator로 축소한다.
- `backend/app/api/routes/ai_gateway.py`
  - 필요 시 리더 결과 검증용 테스트 훅 또는 fixture 정리에만 제한적으로 수정한다.

### New files to create

- `backend/app/agents/services/answer_composer.py`
  - 결과 필터링, rerank, answer slot 추출, 최종 요약 담당.
- `backend/app/agents/services/concept_resolution_service.py`
  - concept 탐지, keyword 보강, synonym fallback, relation expansion 담당.
- `backend/app/agents/services/routing_policy.py`
  - concept 분류, decision rule 적용, selected/rejected agent 계산 담당.
- `backend/app/agents/services/execution_planner.py`
  - `ExecutionPlan`, `ExecutionStep` 생성 및 실행 순서 정책 담당.
- `backend/app/agents/services/clarification_service_adapter.py`
  - pending clarification load/save/clear 분기 정리 담당.

### Existing reference files

- `backend/app/agents/agent_registry.py`
  - `agent_concept_mapping` 기반 라우팅 규칙 참조.
- `backend/app/knowledge/concept_service.py`
  - concept 검색, alias 탐지, concept-api 매핑 참조.
- `backend/app/orchestrator/executor.py`
  - 실제 실행기와 planner 경계 재정립 시 참조.
- `backend/app/agents/validator.py`
  - validation 책임은 유지하고 leader 호출부만 단순화한다.

### Test files

- Create: `backend/tests/agents/test_leader_golden.py`
  - 리팩토링 전후 주요 동작 회귀 확인용 golden baseline 테스트.

---

### Task 1: Golden Baseline 확보

**Files:**
- Create: `backend/tests/agents/test_leader_golden.py`
- Reference: `backend/app/api/routes/ai_gateway.py`

- [ ] **Step 1: 대표 시나리오 5개 선정**

다음 범주를 포함하는 입력을 고른다.

```text
1. 상품 조회
2. 금리 조회
3. 상품 + 금리 복합 질의
4. 정책/서류 질의
5. clarification 필요한 질의
```

- [ ] **Step 2: 핵심 비교 항목 정의**

비교 항목은 완전 문자열 일치가 아니라 핵심 동작 일치로 둔다.

```python
baseline_fields = {
    "detected_concepts": [...],
    "routed_agents": [...],
    "step_api_ids": [...],
    "answer_contains": [...],
    "needs_clarification": False,
}
```

- [ ] **Step 3: failing test 형태의 golden test 초안 작성**

```python
def test_leader_golden_product_query(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "대출 상품 종류 알려줘", "session_id": "golden-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "CONCEPT_LOAN_PRODUCT" in body["plan"]["detected_concepts"]
    assert any(r["api_id"] == "MOCK_PRODUCT_LOOKUP" for r in body["results"])
    assert "대출" in body["answer"]
```

- [ ] **Step 4: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS 또는 현재 테스트 환경 기준 import/setup 오류만 확인 가능
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/agents/test_leader_golden.py
git commit -m "test: add leader golden baseline coverage"
```

---

### Task 2: AnswerComposer 분리

**Files:**
- Create: `backend/app/agents/services/answer_composer.py`
- Modify: `backend/app/agents/leader.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: 리더 내부 요약 책임 메서드 식별**

옮길 대상 후보를 정리한다.

```python
answer_methods = [
    "_filter_results_by_question",
    "_extract_answer_slots",
    "_summarize",
    # rerank / slot ranking 관련 private helpers
]
```

- [ ] **Step 2: failing regression expectation 추가**

```python
def test_leader_answer_composition_still_returns_summary_shape(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 얼마야?", "session_id": "golden-compose"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert isinstance(body["results"], list)
```

- [ ] **Step 3: 최소 구현으로 `AnswerComposer` 생성**

```python
class AnswerComposer:
    async def compose(
        self,
        db,
        request_id: str,
        message: str,
        intent_data: dict,
        classified,
        raw_results,
        history,
        ltm_history,
    ):
        filtered_results = self._filter_results_by_question(message, raw_results, db=db)
        answer_slots = self._extract_answer_slots(classified)
        slot_rankings = []
        answer = await self._summarize(
            message=message,
            results=filtered_results,
            intent_data=intent_data,
            history=history,
            ltm_history=ltm_history,
        )
        return answer, filtered_results, answer_slots, slot_rankings
```

- [ ] **Step 4: 리더 호출부 전환**

```python
composer = AnswerComposer()
answer, ranked_results, answer_slots, slot_rankings = await composer.compose(
    db=db,
    request_id=request_id,
    message=message,
    intent_data=intent_data,
    classified=classified,
    raw_results=raw_results,
    history=history,
    ltm_history=ltm_history,
)
```

- [ ] **Step 5: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/services/answer_composer.py backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: extract answer composition from leader"
```

---

### Task 3: ConceptResolutionService 분리

**Files:**
- Create: `backend/app/agents/services/concept_resolution_service.py`
- Modify: `backend/app/agents/leader.py`
- Reference: `backend/app/knowledge/concept_service.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: concept resolution 출력 구조 정의**

```python
from dataclasses import dataclass


@dataclass
class ResolvedConcepts:
    detected: list[str]
    all_concepts: list[str]
    detected_set: set[str]
```

- [ ] **Step 2: failing regression expectation 추가**

```python
def test_leader_concept_resolution_keeps_interest_rate_detection(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 얼마야?", "session_id": "golden-concept"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "CONCEPT_INTEREST_RATE" in body["plan"]["detected_concepts"]
```

- [ ] **Step 3: 최소 구현으로 resolution 서비스 생성**

```python
class ConceptResolutionService:
    def resolve(self, db, message: str, intent_keywords: list[str]) -> ResolvedConcepts:
        detected = []
        detected_set = set()

        for concept in detect_concepts_in_message(db, message):
            if concept.concept_id not in detected_set:
                detected.append(concept.concept_id)
                detected_set.add(concept.concept_id)

        for kw in intent_keywords:
            kw = kw.strip()
            if len(kw) <= 1:
                continue
            for concept in search_concepts(db, kw):
                if concept.concept_id not in detected_set:
                    detected.append(concept.concept_id)
                    detected_set.add(concept.concept_id)

        all_concepts = list(detected)
        return ResolvedConcepts(
            detected=detected,
            all_concepts=all_concepts,
            detected_set=detected_set,
        )
```

- [ ] **Step 4: synonym fallback, relation expansion 로직 단계적으로 이동**

```python
fallback_concepts = self._detect_concepts_via_synonyms(message, db)
for concept_id in fallback_concepts:
    if concept_id not in detected_set:
        detected.append(concept_id)
        detected_set.add(concept_id)
```

- [ ] **Step 5: 리더 호출부 전환**

```python
resolved = concept_resolution_service.resolve(
    db=db,
    message=message,
    intent_keywords=intent_data.get("keywords", []),
)
detected = resolved.detected
all_concepts = resolved.all_concepts
detected_set = resolved.detected_set
```

- [ ] **Step 6: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/services/concept_resolution_service.py backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: extract concept resolution from leader"
```

---

### Task 4: RoutingPolicy 분리

**Files:**
- Create: `backend/app/agents/services/routing_policy.py`
- Modify: `backend/app/agents/leader.py`
- Reference: `backend/app/agents/agent_registry.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: routing 출력 구조 정의**

```python
from dataclasses import dataclass


@dataclass
class RoutingDecision:
    classified: object
    routed_agents: list[str]
    triggered_rules: list[dict]
    selected_agents_v2: list
    rejected_agents_v2: list
```

- [ ] **Step 2: failing regression expectation 추가**

```python
def test_leader_routing_keeps_rate_agent_for_rate_query(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 얼마야?", "session_id": "golden-route"},
    )
    assert response.status_code == 200
    body = response.json()
    routed = body["plan"]["routed_agents"]
    assert "RATE_AGENT" in routed
```

- [ ] **Step 3: 최소 구현으로 routing policy 생성**

```python
class RoutingPolicy:
    def route(self, db, all_concepts, detected, intent_keywords):
        routing = route_by_concepts(db, all_concepts)
        routed_agents = [item.agent_id for item in routing.routing]
        classified = self._classify_concepts(
            detected=detected,
            all_concepts=all_concepts,
            detected_set=set(detected),
        )
        triggered_rules, selected_agents_v2, rejected_agents_v2 = self._evaluate_decision_rules(
            classified=classified,
            routed_agents=routed_agents,
            all_agents=list(_AGENT_REGISTRY.keys()),
            intent_keywords=intent_keywords,
        )
        return RoutingDecision(
            classified=classified,
            routed_agents=routed_agents,
            triggered_rules=triggered_rules,
            selected_agents_v2=selected_agents_v2,
            rejected_agents_v2=rejected_agents_v2,
        )
```

- [ ] **Step 4: 리더 호출부 전환**

```python
routing_decision = routing_policy.route(
    db=db,
    all_concepts=all_concepts,
    detected=detected,
    intent_keywords=intent_data.get("keywords", []),
)
classified = routing_decision.classified
routed_agents = routing_decision.routed_agents
```

- [ ] **Step 5: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/services/routing_policy.py backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: extract routing policy from leader"
```

---

### Task 5: ExecutionPlanner 분리

**Files:**
- Create: `backend/app/agents/services/execution_planner.py`
- Modify: `backend/app/agents/leader.py`
- Reference: `backend/app/orchestrator/executor.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: planner regression expectation 추가**

```python
def test_leader_plan_keeps_expected_api_for_rate_query(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "신용대출 금리 얼마야?", "session_id": "golden-plan"},
    )
    assert response.status_code == 200
    body = response.json()
    api_ids = [step["api_id"] for step in body["plan"]["steps"]]
    assert "MOCK_RATE_LOOKUP" in api_ids
```

- [ ] **Step 2: 최소 구현으로 planner 생성**

```python
class ExecutionPlanner:
    def build_plan(
        self,
        request_id: str,
        message: str,
        detected_concepts: list[str],
        routed_agents: list[str],
        steps: list,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            request_id=request_id,
            message=message,
            detected_concepts=detected_concepts,
            routed_agents=routed_agents,
            steps=steps,
        )
```

- [ ] **Step 3: step 생성 로직 이동**

```python
steps.append(
    ExecutionStep(
        step_index=step_index,
        agent_id=agent_id,
        concept_id=concept_id,
        api_id=api.api_id,
        params=params,
    )
)
```

- [ ] **Step 4: 리더 호출부 전환**

```python
plan = execution_planner.build_plan(
    request_id=request_id,
    message=message,
    detected_concepts=detected,
    routed_agents=routed_agents,
    steps=steps,
)
```

- [ ] **Step 5: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/services/execution_planner.py backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: extract execution planner from leader"
```

---

### Task 6: Clarification 분기 정리

**Files:**
- Create: `backend/app/agents/services/clarification_service_adapter.py`
- Modify: `backend/app/agents/leader.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: clarification regression expectation 추가**

```python
def test_leader_clarification_flow_still_requests_missing_slot(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "대출 신청하려면?", "session_id": "golden-clarify"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "needs_clarification" in body
```

- [ ] **Step 2: adapter 최소 구현**

```python
class ClarificationServiceAdapter:
    def load_pending(self, session_id: str | None):
        if not session_id:
            return None
        from app.agents.clarification_service import ClarificationService
        return ClarificationService.load_pending(session_id)
```

- [ ] **Step 3: 리더 조건 분기 축소**

```python
pending = clarification_adapter.load_pending(session_id)
clarification_result = clarification_adapter.try_resolve(
    session_id=session_id,
    pending=pending,
    message=message,
)
if clarification_result is not None:
    return clarification_result
```

- [ ] **Step 4: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/services/clarification_service_adapter.py backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: extract clarification coordination from leader"
```

---

### Task 7: LeaderAgent.run 축소

**Files:**
- Modify: `backend/app/agents/leader.py`
- Test: `backend/tests/agents/test_leader_golden.py`

- [ ] **Step 1: 최종 orchestration shape 정리**

```python
history = load_history(session_id)
ltm_history = load_long_term_history(db, session_id, user_id=owner_name)
intent_data = await intent_service.analyze(message, history, ltm_history)
resolved = concept_resolution_service.resolve(db, message, intent_data.get("keywords", []))
routing_decision = routing_policy.route(db, resolved.all_concepts, resolved.detected, intent_data.get("keywords", []))
plan = execution_planner.build_plan(...)
raw_results = await execute_plan(db, plan, intent=intent_data.get("intent", "INQUIRY"))
answer, ranked_results, answer_slots, slot_rankings = await answer_composer.compose(...)
validation = validation_checker.run_all(...)
```

- [ ] **Step 2: 리더 내부 잔여 private helper 점검**

```text
남아 있는 helper가 "trace 조립", "result assembly", "예외 정규화" 성격인지 확인한다.
도메인 판단이나 포맷팅이 남아 있으면 다시 서비스로 이동한다.
```

- [ ] **Step 3: 테스트 실행**

Run:

```bash
pytest backend/tests/agents/test_leader_golden.py -v
```

Expected:

```text
PASS
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/leader.py backend/tests/agents/test_leader_golden.py
git commit -m "refactor: slim leader agent orchestration"
```

---

### Task 8: 검증과 2차 후보 정리

**Files:**
- Test: `backend/tests/agents/test_leader_golden.py`
- Optional: `docs/leader-refactor-notes.md`

- [ ] **Step 1: 전체 관련 테스트 실행**

Run:

```bash
pytest backend/tests/agents -v
```

Expected:

```text
PASS
```

- [ ] **Step 2: 회귀 점검 항목 기록**

```text
1. detected concepts 유지 여부
2. routed agents 유지 여부
3. plan step api_id 유지 여부
4. clarification 동작 유지 여부
5. 최종 answer 핵심 문구 유지 여부
6. trace/evidence 저장 누락 여부
```

- [ ] **Step 3: 2차 리팩토링 후보 제한**

```text
1. AnswerComposer 내부를 ranking / summary_builder로 재분리
2. DECISION_RULES와 keyword map의 DB 또는 설정 파일 외부화
3. LeaderDecisionV2 builder 별도 서비스 분리
```

- [ ] **Step 4: Commit**

```bash
git add docs/leader-refactor-notes.md
git commit -m "docs: capture leader refactor follow-up notes"
```

---

## Self-Review

### Spec coverage

- 리더 비대화의 주요 원인인 concept 해석, agent 선택 보정, 요약, clarification, plan 생성이 모두 별도 task로 분리되어 있다.
- `agent_concept_mapping` 기반 선택 원칙은 유지되며, LLM 임의 선택 구조로 바꾸지 않는다.
- 1차에서는 동작 변경보다 책임 이동에 집중하도록 범위를 제한했다.

### Placeholder scan

- `TODO`, `TBD`, "적절히 처리" 같은 표현 없이 구체 파일과 단계가 들어가 있다.
- 테스트, 실행 명령, 기대 결과, 커밋 단위가 각 task에 포함되어 있다.

### Type consistency

- `ResolvedConcepts`, `RoutingDecision`, `AnswerComposer`, `ExecutionPlanner` 기준으로 서비스 경계를 일관되게 잡았다.
- 실제 구현 시 현재 `LeaderResult`, `ExecutionPlan`, `ExecutionStep`, `StepResult` 스키마와 이름 충돌이 없는지 확인이 필요하다.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-leader-agent-slimming.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

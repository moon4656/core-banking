# Decision Trace MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 운영자가 사용자 질문부터 Concept, Agent, Tool, Evidence, Final Answer grounding까지 한 요청의 의사결정 흐름을 추적할 수 있는 Decision Trace MVP를 구현한다.

**Architecture:** 기존 `trace_event`, `leader_decision`, `evidence_reference`, `leader_decision_node/edge`를 유지하면서, 먼저 canonical decision-trace 데이터를 추가 저장하고 그 위에 읽기 API와 UI를 얹는다. MVP에서는 Agent 구조를 바꾸지 않고 `LeaderAgent.run()` 내부에서 intent/concept/agent/tool/reranking/final-answer 메타데이터를 구조화해 저장한 뒤, `/api/v1/ai/decisions/{request_id}/trace` 응답으로 Summary / Decision Trace / Evidence Tool View를 제공한다.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL JSONB, Next.js App Router, React Query, MUI, existing React Flow UI

---

## File Map

**Backend core**
- Modify: `backend/app/models/trace_model.py`
  - Decision trace canonical storage용 테이블/컬럼 정의
- Modify: `backend/app/agents/leader.py`
  - intent/concept/agent/tool/reranking/final-answer 추적 데이터 생성
- Modify: `backend/app/agents/agent_registry.py`
  - selected/rejected agent 판단 결과를 설명 가능한 구조로 확장
- Modify: `backend/app/trace/evidence_service.py`
  - evidence와 final grounding 연결에 필요한 필드 보강
- Create: `backend/app/schemas/decision_trace.py`
  - Decision Trace API 응답 스키마
- Create: `backend/app/services/decision_trace_service.py`
  - request_id 기준 canonical trace 조회/조립
- Modify: `backend/app/api/routes/decisions.py`
  - 상세 graph API와 별도 trace API 연결
- Create: `backend/alembic/versions/0007_add_decision_trace_mvp.py`
  - DB migration

**Frontend**
- Modify: `frontend/src/lib/api.ts`
  - decision trace fetch 타입/함수 추가
- Create: `frontend/src/types/decisionTrace.ts`
  - UI 전용 타입
- Modify: `frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx`
  - Summary / Decision Trace / Evidence Tool 탭 UI
- Create: `frontend/src/components/decision-trace/SummaryView.tsx`
  - Summary View
- Create: `frontend/src/components/decision-trace/DecisionTraceView.tsx`
  - Concept/Agent/Reranking 흐름 표시
- Create: `frontend/src/components/decision-trace/EvidenceToolView.tsx`
  - Tool/Evidence/Final grounding 표시

**Tests**
- Modify: `backend/tests/test_chat.py`
  - 기존 trace 회귀 보강
- Create: `backend/tests/test_decision_trace.py`
  - decision trace canonical 저장/응답 검증

---

### Task 1: Add Failing Backend Tests For Canonical Decision Trace

**Files:**
- Create: `backend/tests/test_decision_trace.py`
- Modify: `backend/tests/test_chat.py`

- [ ] **Step 1: Write the failing canonical trace API test**

```python
from fastapi.testclient import TestClient


def test_decision_trace_detail_contains_mvp_fields(client: TestClient, auth_headers_analyst):
    chat_res = client.post(
        "/api/v1/ai/chat",
        headers=auth_headers_analyst,
        json={"message": "신용대출 금리와 필요서류 알려줘", "session_id": "trace-mvp-001"},
    )
    assert chat_res.status_code == 200
    request_id = chat_res.json()["request_id"]

    trace_res = client.get(
        f"/api/v1/ai/decisions/{request_id}/trace",
        headers=auth_headers_analyst,
    )

    assert trace_res.status_code == 200
    payload = trace_res.json()
    assert payload["request_id"] == request_id
    assert payload["user_query"]
    assert payload["intent_analysis"]["intent"]
    assert isinstance(payload["concepts"], list)
    assert "selected_agents" in payload["agent_selection"]
    assert "rejected_agents" in payload["agent_selection"]
    assert isinstance(payload["tool_executions"], list)
    assert "final_answer" in payload
    assert "latency" in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_decision_trace.py::test_decision_trace_detail_contains_mvp_fields -v`

Expected: FAIL with `404` on `/api/v1/ai/decisions/{request_id}/trace` or missing response keys

- [ ] **Step 3: Add a failing persistence-level regression test**

```python
def test_chat_persists_selected_and_rejected_agent_reasons(client: TestClient, db, auth_headers_analyst):
    chat_res = client.post(
        "/api/v1/ai/chat",
        headers=auth_headers_analyst,
        json={"message": "신용대출 금리 알려줘", "session_id": "trace-mvp-002"},
    )
    assert chat_res.status_code == 200
    request_id = chat_res.json()["request_id"]

    rows = db.execute(
        "SELECT agent_id, selected, reason FROM ai_agent_selection WHERE request_id = :rid",
        {"rid": request_id},
    ).fetchall()

    assert rows
    assert any(row[1] is True for row in rows)
    assert any(row[1] is False for row in rows)
    assert all(row[2] for row in rows)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest backend/tests/test_decision_trace.py::test_chat_persists_selected_and_rejected_agent_reasons -v`

Expected: FAIL with missing table `ai_agent_selection`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_decision_trace.py backend/tests/test_chat.py
git commit -m "test: add failing decision trace mvp coverage"
```

---

### Task 2: Add Decision Trace Storage Schema

**Files:**
- Modify: `backend/app/models/trace_model.py`
- Create: `backend/alembic/versions/0007_add_decision_trace_mvp.py`

- [ ] **Step 1: Add the new SQLAlchemy models**

```python
class DecisionTrace(Base):
    __tablename__ = "ai_decision_trace"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    user_query = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)
    request_meta = Column(JSONB, nullable=True, default=dict)
    memory_summary = Column(JSONB, nullable=True, default=dict)
    intent_analysis = Column(JSONB, nullable=True, default=dict)
    latency = Column(JSONB, nullable=True, default=dict)
    status = Column(String(32), nullable=False, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ConceptDetectionTrace(Base):
    __tablename__ = "ai_concept_detection"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    concept_id = Column(String(100), nullable=False, index=True)
    detection_stage = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=True)
    source_type = Column(String(32), nullable=True)
    source_terms = Column(JSONB, nullable=True, default=list)
    relation_path = Column(JSONB, nullable=True, default=list)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AgentSelectionTrace(Base):
    __tablename__ = "ai_agent_selection"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    selected = Column(Boolean, nullable=False, default=False)
    score = Column(Float, nullable=True)
    matched_concepts = Column(JSONB, nullable=True, default=list)
    reason = Column(Text, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ToolExecutionTrace(Base):
    __tablename__ = "ai_tool_execution"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    tool_code = Column(String(100), nullable=False, index=True)
    concept_ids = Column(JSONB, nullable=True, default=list)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    status = Column(String(32), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    error_summary = Column(Text, nullable=True)
    evidence_ids = Column(JSONB, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RerankingTrace(Base):
    __tablename__ = "ai_reranking_trace"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    criteria_weights = Column(JSONB, nullable=True, default=dict)
    candidates = Column(JSONB, nullable=True, default=list)
    selected_evidence_ids = Column(JSONB, nullable=True, default=list)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FinalAnswerTrace(Base):
    __tablename__ = "ai_final_answer_trace"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, unique=True, index=True)
    answer = Column(Text, nullable=False)
    answer_summary = Column(Text, nullable=True)
    used_evidence_ids = Column(JSONB, nullable=True, default=list)
    grounding_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 2: Add the Alembic migration**

```python
def upgrade() -> None:
    op.create_table(
        "ai_decision_trace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.Text(), nullable=True),
        sa.Column("request_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("memory_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("intent_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_decision_trace_request_id", "ai_decision_trace", ["request_id"], unique=True)
    op.create_index("ix_ai_decision_trace_session_id", "ai_decision_trace", ["session_id"], unique=False)

    # Repeat for ai_concept_detection, ai_agent_selection, ai_tool_execution,
    # ai_reranking_trace, ai_final_answer_trace with request_id-based indexes.
```

- [ ] **Step 3: Run migration**

Run: `docker compose exec backend alembic upgrade head`

Expected: PASS with migration `0007_add_decision_trace_mvp`

- [ ] **Step 4: Verify schema exists**

Run: `docker compose exec backend pytest backend/tests/test_decision_trace.py::test_chat_persists_selected_and_rejected_agent_reasons -v`

Expected: FAIL moves from missing table to missing persistence logic

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/trace_model.py backend/alembic/versions/0007_add_decision_trace_mvp.py
git commit -m "feat: add decision trace mvp storage schema"
```

---

### Task 3: Implement Decision Trace Persistence Service

**Files:**
- Create: `backend/app/services/decision_trace_service.py`
- Modify: `backend/app/agents/leader.py`
- Modify: `backend/app/agents/agent_registry.py`

- [ ] **Step 1: Add the trace persistence service helpers**

```python
from app.models.trace_model import (
    AgentSelectionTrace,
    ConceptDetectionTrace,
    DecisionTrace,
    FinalAnswerTrace,
    RerankingTrace,
    ToolExecutionTrace,
)


def save_decision_trace_core(
    db,
    *,
    request_id: str,
    session_id: str | None,
    user_query: str,
    normalized_query: str,
    request_meta: dict,
    memory_summary: dict,
    intent_analysis: dict,
    latency: dict,
) -> None:
    db.add(
        DecisionTrace(
            request_id=request_id,
            session_id=session_id,
            user_query=user_query,
            normalized_query=normalized_query,
            request_meta=request_meta,
            memory_summary=memory_summary,
            intent_analysis=intent_analysis,
            latency=latency,
        )
    )


def save_concept_detections(db, request_id: str, concepts: list[dict]) -> None:
    for concept in concepts:
        db.add(
            ConceptDetectionTrace(
                request_id=request_id,
                concept_id=concept["concept_id"],
                detection_stage=concept["detection_stage"],
                confidence=concept.get("confidence"),
                source_type=concept.get("source_type"),
                source_terms=concept.get("source_terms", []),
                relation_path=concept.get("relation_path", []),
                reason=concept.get("reason"),
            )
        )
```

- [ ] **Step 2: Expand routing output to include rejected agents**

```python
@dataclass
class AgentCandidate:
    agent_id: str
    selected: bool
    matched_concepts: list[str]
    reason: str
    rejection_reason: str | None = None
    score: float | None = None
```

```python
def route_by_concepts(db: Session, concept_ids: list[str]) -> AgentRouteResponse:
    # existing routing logic 유지
    # plus all active agents를 기준으로 selected=False 후보를 채운다
    # 예: concept 미매칭이면 "요청 concept와 매핑 없음"
```

- [ ] **Step 3: Build structured intent/concept/latency payloads inside `LeaderAgent.run()`**

```python
normalized_query = " ".join(message.split())

intent_analysis = {
    "intent": intent_data.get("intent"),
    "confidence": intent_data.get("confidence", 0.75),
    "keywords": intent_data.get("keywords", []),
    "urgency": intent_data.get("urgency", "low"),
    "reason": intent_data.get(
        "reason",
        f"keywords={intent_data.get('keywords', [])} based intent classification",
    ),
}

concept_trace_rows = []
for cid in detected:
    concept_trace_rows.append(
        {
            "concept_id": cid,
            "detection_stage": "direct",
            "confidence": 0.95,
            "source_type": "query",
            "source_terms": [term for term in search_terms if term and cid in [c.concept_id for c in search_concepts(db, term)]][:3],
            "reason": "Matched from query term or intent keyword",
        }
    )
for cid in [c for c in all_concepts if c not in detected_set]:
    concept_trace_rows.append(
        {
            "concept_id": cid,
            "detection_stage": "expanded",
            "confidence": 0.7,
            "source_type": "ontology",
            "source_terms": [],
            "reason": "Expanded via business_concept_relation weight >= 0.7",
        }
    )
```

- [ ] **Step 4: Persist tool executions, reranking, and final grounding**

```python
tool_execution_rows = []
evidence_ids_by_api: dict[str, list[int]] = {}

# evidence 저장 직후
saved = _save_ev(...)
evidence_ids_by_api.setdefault(api_res["api_id"], []).append(saved.id)

tool_execution_rows.append(
    {
        "agent_id": route_item.agent_id,
        "tool_code": api_res["api_id"],
        "concept_ids": route_item.concept_ids,
        "input_summary": f"api_id={api_res['api_id']} concepts={route_item.concept_ids}",
        "output_summary": f"status={api_res['status']} keys={list((api_res.get('data') or {}).keys())[:3]}",
        "status": api_res["status"],
        "latency_ms": api_res.get("latency_ms"),
        "error_summary": api_res.get("error"),
        "evidence_ids": evidence_ids_by_api.get(api_res["api_id"], []),
    }
)
```

```python
rerank_candidates = []
for rank, result in enumerate(ranked_results, start=1):
    rerank_candidates.append(
        {
            "source_id": result.api_id,
            "rank": rank,
            "status": result.status,
            "score_breakdown": {
                "success": 1.0 if result.status == "success" else 0.0,
                "intent_relevance": 0.5 if result.api_id in _API_INTENT_RELEVANCE else 0.0,
            },
        }
    )
```

- [ ] **Step 5: Commit transaction once after trace records are added**

```python
save_decision_trace_core(...)
save_concept_detections(...)
save_agent_selection_rows(...)
save_tool_execution_rows(...)
save_reranking_trace(...)
save_final_answer_trace(...)
db.commit()
```

- [ ] **Step 6: Run focused tests**

Run: `pytest backend/tests/test_decision_trace.py -v`

Expected: PASS for persistence tests

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/decision_trace_service.py backend/app/agents/leader.py backend/app/agents/agent_registry.py
git commit -m "feat: persist canonical decision trace data"
```

---

### Task 4: Add Decision Trace Read Schema And API

**Files:**
- Create: `backend/app/schemas/decision_trace.py`
- Modify: `backend/app/api/routes/decisions.py`
- Modify: `backend/app/services/decision_trace_service.py`

- [ ] **Step 1: Define the response schema**

```python
class MemoryBucket(BaseModel):
    loaded: bool
    summary: str | None = None
    items_count: int = 0
    impact: list[str] = Field(default_factory=list)


class IntentAnalysisResponse(BaseModel):
    intent: str | None
    confidence: float | None
    keywords: list[str] = Field(default_factory=list)
    urgency: str | None = None
    reason: str | None = None


class ConceptTraceResponse(BaseModel):
    concept_id: str
    detection_stage: str
    confidence: float | None
    source_type: str | None
    source_terms: list[str] = Field(default_factory=list)
    reason: str | None


class AgentSelectionItemResponse(BaseModel):
    agent_name: str
    selected: bool
    score: float | None
    matched_concepts: list[str] = Field(default_factory=list)
    reason: str
    rejection_reason: str | None = None


class ToolExecutionResponse(BaseModel):
    tool_name: str
    agent_name: str
    concept_ids: list[str] = Field(default_factory=list)
    input_summary: str | None
    output_summary: str | None
    status: str
    latency_ms: int | None
    evidence_ids: list[int] = Field(default_factory=list)


class DecisionTraceDetailResponse(BaseModel):
    request_id: str
    user_query: str
    normalized_query: str | None
    memory: dict[str, MemoryBucket]
    intent_analysis: IntentAnalysisResponse
    concepts: list[ConceptTraceResponse]
    agent_selection: dict[str, list[AgentSelectionItemResponse]]
    tool_executions: list[ToolExecutionResponse]
    reranking: dict[str, Any]
    final_answer: dict[str, Any]
    latency: dict[str, Any]
```

- [ ] **Step 2: Add read-model assembly code**

```python
def get_decision_trace_detail(db, request_id: str) -> DecisionTraceDetailResponse:
    trace = db.query(DecisionTrace).filter_by(request_id=request_id).first()
    if trace is None:
        raise ValueError("decision trace not found")

    concept_rows = (
        db.query(ConceptDetectionTrace)
        .filter_by(request_id=request_id)
        .order_by(ConceptDetectionTrace.id.asc())
        .all()
    )
    agent_rows = db.query(AgentSelectionTrace).filter_by(request_id=request_id).all()
    tool_rows = db.query(ToolExecutionTrace).filter_by(request_id=request_id).all()
    rerank = db.query(RerankingTrace).filter_by(request_id=request_id).first()
    final = db.query(FinalAnswerTrace).filter_by(request_id=request_id).first()

    return DecisionTraceDetailResponse(
        request_id=trace.request_id,
        user_query=trace.user_query,
        normalized_query=trace.normalized_query,
        memory=trace.memory_summary,
        intent_analysis=trace.intent_analysis,
        concepts=[...],
        agent_selection={
            "selected_agents": [...],
            "rejected_agents": [...],
        },
        tool_executions=[...],
        reranking={...},
        final_answer={...},
        latency=trace.latency,
    )
```

- [ ] **Step 3: Expose the new route**

```python
@router.get("/decisions/{request_id}/trace", response_model=DecisionTraceDetailResponse)
def get_decision_trace(
    request_id: str,
    db: Session = Depends(get_db),
    _: Role = Depends(require_readonly),
):
    try:
        return get_decision_trace_detail(db, request_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision trace not found")
```

- [ ] **Step 4: Run focused API test**

Run: `pytest backend/tests/test_decision_trace.py::test_decision_trace_detail_contains_mvp_fields -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/decision_trace.py backend/app/services/decision_trace_service.py backend/app/api/routes/decisions.py
git commit -m "feat: add decision trace detail api"
```

---

### Task 5: Add Failing Frontend Tests And Types

**Files:**
- Create: `frontend/src/types/decisionTrace.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add the frontend type definitions**

```typescript
export type DecisionTraceConcept = {
  concept_id: string;
  detection_stage: "direct" | "expanded";
  confidence: number | null;
  source_type: "query" | "memory" | "ontology" | null;
  source_terms: string[];
  reason: string | null;
};

export type DecisionTraceAgentSelectionItem = {
  agent_name: string;
  selected: boolean;
  score: number | null;
  matched_concepts: string[];
  reason: string;
  rejection_reason: string | null;
};

export type DecisionTraceDetail = {
  request_id: string;
  user_query: string;
  normalized_query: string | null;
  memory: Record<string, {
    loaded: boolean;
    summary: string | null;
    items_count: number;
    impact: string[];
  }>;
  intent_analysis: {
    intent: string | null;
    confidence: number | null;
    keywords: string[];
    urgency: string | null;
    reason: string | null;
  };
  concepts: DecisionTraceConcept[];
  agent_selection: {
    selected_agents: DecisionTraceAgentSelectionItem[];
    rejected_agents: DecisionTraceAgentSelectionItem[];
  };
  tool_executions: Array<{
    tool_name: string;
    agent_name: string;
    concept_ids: string[];
    input_summary: string | null;
    output_summary: string | null;
    status: string;
    latency_ms: number | null;
    evidence_ids: number[];
  }>;
  reranking: Record<string, unknown>;
  final_answer: Record<string, unknown>;
  latency: Record<string, unknown>;
};
```

- [ ] **Step 2: Add API helper**

```typescript
export function fetchDecisionTrace(requestId: string) {
  return apiGet<DecisionTraceDetail>(`/api/v1/ai/decisions/${requestId}/trace`);
}
```

- [ ] **Step 3: Run type check to verify current UI is still green**

Run: `npm run build`

Expected: PASS or unrelated pre-existing frontend warnings only

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/decisionTrace.ts frontend/src/lib/api.ts
git commit -m "feat: add frontend decision trace types"
```

---

### Task 6: Implement Summary View

**Files:**
- Create: `frontend/src/components/decision-trace/SummaryView.tsx`
- Modify: `frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx`

- [ ] **Step 1: Create the summary component**

```tsx
import { Chip, Stack, Typography } from "@mui/material";
import { DecisionTraceDetail } from "@/types/decisionTrace";

export function SummaryView({ trace }: { trace: DecisionTraceDetail }) {
  const selected = trace.agent_selection.selected_agents;
  const rejected = trace.agent_selection.rejected_agents;
  const totalMs = Number((trace.latency as { total_ms?: number }).total_ms ?? 0);

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="overline">User Query</Typography>
        <Typography variant="body1">{trace.user_query}</Typography>
      </div>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip label={`Intent: ${trace.intent_analysis.intent ?? "-"}`} color="info" />
        <Chip label={`Selected Agent: ${selected.length}`} />
        <Chip label={`Rejected Agent: ${rejected.length}`} />
        <Chip label={`Tool: ${trace.tool_executions.length}`} />
        <Chip label={`Latency: ${totalMs}ms`} />
      </Stack>

      <div>
        <Typography variant="overline">Grounding</Typography>
        <Typography variant="body2">
          {String((trace.final_answer as { grounding_summary?: string }).grounding_summary ?? "-")}
        </Typography>
      </div>
    </Stack>
  );
}
```

- [ ] **Step 2: Load both graph and trace in the page**

```tsx
const traceQuery = useQuery({
  queryKey: ["decision-trace", requestId],
  queryFn: () => fetchDecisionTrace(requestId),
});
```

- [ ] **Step 3: Render Summary tab**

```tsx
{activeTab === "summary" && traceQuery.data ? (
  <SummaryView trace={traceQuery.data} />
) : null}
```

- [ ] **Step 4: Run build**

Run: `npm run build`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/decision-trace/SummaryView.tsx frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx
git commit -m "feat: add decision trace summary view"
```

---

### Task 7: Implement Decision Trace View

**Files:**
- Create: `frontend/src/components/decision-trace/DecisionTraceView.tsx`
- Modify: `frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx`

- [ ] **Step 1: Add the concept and agent reasoning component**

```tsx
import { Alert, Divider, Stack, Typography } from "@mui/material";
import { DecisionTraceDetail } from "@/types/decisionTrace";

export function DecisionTraceView({ trace }: { trace: DecisionTraceDetail }) {
  return (
    <Stack spacing={2}>
      <section>
        <Typography variant="subtitle2">Intent</Typography>
        <Typography variant="body2">
          {trace.intent_analysis.intent} / confidence {trace.intent_analysis.confidence ?? "-"}
        </Typography>
        <Typography variant="caption">{trace.intent_analysis.reason ?? "-"}</Typography>
      </section>

      <Divider />

      <section>
        <Typography variant="subtitle2">Concepts</Typography>
        {trace.concepts.map((concept) => (
          <Alert key={`${concept.concept_id}-${concept.detection_stage}`} severity={concept.detection_stage === "direct" ? "success" : "info"}>
            {concept.concept_id} / conf {concept.confidence ?? "-"} / {concept.reason ?? "-"}
          </Alert>
        ))}
      </section>

      <Divider />

      <section>
        <Typography variant="subtitle2">Selected Agents</Typography>
        {trace.agent_selection.selected_agents.map((agent) => (
          <Alert key={agent.agent_name} severity="success">
            {agent.agent_name} / concepts {agent.matched_concepts.join(", ")} / {agent.reason}
          </Alert>
        ))}
      </section>

      <section>
        <Typography variant="subtitle2">Rejected Agents</Typography>
        {trace.agent_selection.rejected_agents.map((agent) => (
          <Alert key={agent.agent_name} severity="warning">
            {agent.agent_name} / {agent.rejection_reason ?? agent.reason}
          </Alert>
        ))}
      </section>
    </Stack>
  );
}
```

- [ ] **Step 2: Add the Decision Trace tab to the page**

```tsx
{activeTab === "trace" && traceQuery.data ? (
  <DecisionTraceView trace={traceQuery.data} />
) : null}
```

- [ ] **Step 3: Run build**

Run: `npm run build`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/decision-trace/DecisionTraceView.tsx frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx
git commit -m "feat: add decision trace reasoning view"
```

---

### Task 8: Implement Evidence / Tool View

**Files:**
- Create: `frontend/src/components/decision-trace/EvidenceToolView.tsx`
- Modify: `frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx`

- [ ] **Step 1: Add the tool/evidence component**

```tsx
import { Alert, Chip, Stack, Typography } from "@mui/material";
import { DecisionTraceDetail } from "@/types/decisionTrace";

export function EvidenceToolView({ trace }: { trace: DecisionTraceDetail }) {
  const finalEvidence = ((trace.final_answer as { used_evidence_ids?: number[] }).used_evidence_ids ?? []) as number[];

  return (
    <Stack spacing={2}>
      <section>
        <Typography variant="subtitle2">Tool Executions</Typography>
        {trace.tool_executions.map((tool) => (
          <Alert key={`${tool.agent_name}-${tool.tool_name}`} severity={tool.status === "success" ? "success" : "error"}>
            <Stack spacing={0.5}>
              <Typography variant="body2">{tool.agent_name} → {tool.tool_name}</Typography>
              <Typography variant="caption">Input: {tool.input_summary ?? "-"}</Typography>
              <Typography variant="caption">Output: {tool.output_summary ?? "-"}</Typography>
              <Typography variant="caption">Latency: {tool.latency_ms ?? "-"}ms</Typography>
            </Stack>
          </Alert>
        ))}
      </section>

      <section>
        <Typography variant="subtitle2">Final Answer Evidence</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {finalEvidence.map((id) => <Chip key={id} label={`Evidence #${id}`} color="success" />)}
        </Stack>
      </section>
    </Stack>
  );
}
```

- [ ] **Step 2: Add the Evidence / Tool tab**

```tsx
{activeTab === "evidence" && traceQuery.data ? (
  <EvidenceToolView trace={traceQuery.data} />
) : null}
```

- [ ] **Step 3: Run build**

Run: `npm run build`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/decision-trace/EvidenceToolView.tsx frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx
git commit -m "feat: add decision trace evidence tool view"
```

---

### Task 9: Verification And Cleanup

**Files:**
- Modify: `backend/tests/test_decision_trace.py`
- Modify: `backend/tests/test_chat.py`
- Modify: `frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx`

- [ ] **Step 1: Add final regression assertions**

```python
def test_decision_trace_detail_includes_grounding_and_latency(client: TestClient, auth_headers_analyst):
    chat_res = client.post(
        "/api/v1/ai/chat",
        headers=auth_headers_analyst,
        json={"message": "신용대출 금리와 우대금리 알려줘", "session_id": "trace-mvp-003"},
    )
    request_id = chat_res.json()["request_id"]

    trace_res = client.get(f"/api/v1/ai/decisions/{request_id}/trace", headers=auth_headers_analyst)
    payload = trace_res.json()

    assert "total_ms" in payload["latency"]
    assert "grounding_summary" in payload["final_answer"]
```

- [ ] **Step 2: Run backend tests**

Run: `pytest backend/tests/test_chat.py backend/tests/test_decision_trace.py -v`

Expected: PASS

- [ ] **Step 3: Run frontend build**

Run: `npm run build`

Expected: PASS

- [ ] **Step 4: Smoke-check the app**

Run:

```bash
docker compose up -d frontend backend
docker compose logs frontend --tail 40
docker compose logs backend --tail 40
```

Expected: no startup errors, `/admin/decisions/{id}/graph` loads with Summary / Decision Trace / Evidence Tool tabs

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_decision_trace.py backend/tests/test_chat.py frontend/src/app/admin/decisions/[id]/graph/GraphClient.tsx
git commit -m "test: verify decision trace mvp end to end"
```

---

## Spec Coverage Check

- User Query 표시: Task 3, Task 4, Task 6
- Intent 표시: Task 3, Task 4, Task 7
- Concept confidence 표시: Task 3, Task 4, Task 7
- 선택 Agent 표시: Task 3, Task 4, Task 7
- 미선택 Agent 사유 표시: Task 3, Task 4, Task 7
- Tool 실행 결과 표시: Task 3, Task 4, Task 8
- Tool 입력/출력 요약 표시: Task 3, Task 4, Task 8
- Re-ranking 기준 표시: Task 3, Task 4, Task 7
- 최종 답변 근거 표시: Task 3, Task 4, Task 8
- 전체/단계별 latency 표시: Task 3, Task 4, Task 6

## Placeholder Scan

- `TODO`, `TBD`, `implement later` 없음
- 모든 코드 수정 태스크에 실제 파일 경로, 코드 예시, 실행 명령 포함
- migration, API, UI, tests 순서 명시됨

## Type Consistency Check

- Backend canonical names: `ai_decision_trace`, `ai_concept_detection`, `ai_agent_selection`, `ai_tool_execution`, `ai_reranking_trace`, `ai_final_answer_trace`
- API response field names: `user_query`, `intent_analysis`, `concepts`, `agent_selection`, `tool_executions`, `final_answer`, `latency`
- Frontend 동일 타입명 `DecisionTraceDetail` 기준으로 소비


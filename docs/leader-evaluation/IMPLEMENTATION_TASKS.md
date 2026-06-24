# 리더 평가 화면 — 구현 작업 계획 (IMPLEMENTATION_TASKS)

> 구현은 `승인: Leader Evaluation 구현 진행` 메시지 이후에만 시작한다.  
> 각 Phase는 이전 Phase 완료 확인 후 진행한다.

---

## Phase 1. 현재 구조 분석 보완

### 목표
코드 분석만으로 확인하지 못한 런타임 동작을 실제 실행으로 검증한다.

### 수정 대상 파일
없음 (분석 전용)

### 세부 작업

1. Docker 환경 기동 확인
   ```bash
   docker compose ps
   curl http://localhost:18000/health
   curl http://localhost:18010/health
   ```

2. 채팅 요청 1건 실행 후 request_id 획득
   ```bash
   curl -X POST http://localhost:18000/api/v1/ai/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "신용대출 금리 알려줘", "session_id": "test-001"}'
   ```

3. 해당 request_id로 Trace/Evidence 직접 조회
   ```
   GET /api/v1/ai/traces/{request_id}/events
   GET /api/v1/ai/traces/{request_id}/evidence
   GET /api/v1/admin/leader-evaluations/{request_id}
   ```

4. 확인 항목
   - `TOOL_INVOKED` 이벤트의 `tool_id` 실제 null 여부
   - `LeaderDecision.answer` 실제 null 여부
   - `EvidenceReference.source_type` 실제 null 여부
   - `EvidenceReference.agent_id` 컬럼 존재 여부
   - `leader_decision` 테이블 실제 컬럼 목록 (`\d leader_decision`)

### 완료 기준
- 위 4개 확인 항목의 실제 상태가 문서화됨

### 리스크
- Docker 미구동 시 런타임 확인 불가 → 이미 분석된 코드 기준으로 진행 가능

### 금지 사항
- 코드 수정 없음
- DB 스키마 변경 없음

---

## Phase 2. Backend — Trace tool_id 수정

### 목표
`TOOL_INVOKED` 이벤트에서 `tool_id` 필드가 항상 null인 문제를 수정한다.  
DB 스키마 변경 없이 코드만 수정한다.

### 수정 대상 파일
```
backend/app/agents/leader.py  — line 270-277
```

### 세부 작업

`leader.py:270`의 `record_event()` 호출에 `tool_id` 인자 추가:

```python
# 변경 전
record_event(
    db,
    request_id=request_id,
    event_type="TOOL_INVOKED",
    input_data={"api_id": api_res["api_id"], "agent_id": route_item.agent_id},
    output_data={"status": api_res["status"]},
    duration_ms=api_res.get("latency_ms"),
)

# 변경 후
record_event(
    db,
    request_id=request_id,
    event_type="TOOL_INVOKED",
    agent_id=route_item.agent_id,       # 추가
    tool_id=api_res["api_id"],           # 추가
    input_data={"api_id": api_res["api_id"], "agent_id": route_item.agent_id},
    output_data={"status": api_res["status"]},
    duration_ms=api_res.get("latency_ms"),
)
```

`record_event()` 함수 시그니처 확인: `trace_service.py`의 `record_event()`에 `agent_id`, `tool_id` 파라미터가 있는지 확인 후 없으면 추가.

### 완료 기준
- 채팅 요청 후 `TOOL_INVOKED` 이벤트의 `tool_id`가 api_id 값으로 채워짐

### 테스트 방법
```
POST /api/v1/ai/chat → GET /api/v1/ai/traces/{id}/events → TOOL_INVOKED.tool_id 확인
```

### 리스크
- `record_event()` 시그니처 변경 시 다른 호출부 영향 → `trace_service.py` 먼저 확인

### 금지 사항
- `trace_event` 테이블 스키마 변경 없음 (이미 tool_id 컬럼 존재)

---

## Phase 3. Backend — DB 컬럼 추가 + Migration

### 목표
`LeaderDecision`과 `EvidenceReference`에 개선 설계에서 결정된 컬럼을 추가한다.

### 수정 대상 파일
```
backend/app/models/trace_model.py
backend/alembic/versions/xxxx_add_leader_eval_fields.py  (신규 생성)
```

### 세부 작업

**1. `trace_model.py` — LeaderDecision 컬럼 추가**

```python
# leader_decision 테이블에 추가
answer           = Column(Text, nullable=True)            # 최종 LLM 답변
direct_concepts  = Column(JSON, nullable=True)            # 직접 탐지 concept 목록
expanded_concepts = Column(JSON, nullable=True)           # 온톨로지 확장 concept 목록
review_reason    = Column(String(100), nullable=True)     # NEEDS_REVIEW/FAIL 원인 코드
ltm_turns        = Column(Integer, default=0, nullable=True)  # LTM 활용 턴 수
```

**2. `trace_model.py` — EvidenceReference 컬럼 추가**

```python
# evidence_reference 테이블에 추가
agent_id = Column(String(100), nullable=True)
```

**3. Alembic migration 생성**

```bash
docker compose exec backend alembic revision --autogenerate \
  -m "add_leader_eval_fields"
docker compose exec backend alembic upgrade head
```

### 완료 기준
- `\d leader_decision` 에서 5개 새 컬럼 확인
- `\d evidence_reference` 에서 `agent_id` 컬럼 확인
- 기존 레코드 정상 조회 확인

### 테스트 방법
```bash
docker compose exec db psql -U ai_agent -d ai_agent_db \
  -c "\d leader_decision"
docker compose exec db psql -U ai_agent -d ai_agent_db \
  -c "SELECT COUNT(*) FROM leader_decision;"  # 기존 레코드 수 유지 확인
```

### 리스크
- Alembic autogenerate가 nullable 컬럼을 NOT NULL로 생성하는 경우 → 생성된 파일 수동 검토 필수

### 금지 사항
- 기존 컬럼 타입/이름 변경 없음
- 기존 컬럼 삭제 없음

---

## Phase 4. Backend — LeaderDecision 저장 시 신규 필드 채우기

### 목표
Phase 3에서 추가한 컬럼을 `leader.py`에서 실제 값으로 저장하도록 수정한다.

### 수정 대상 파일
```
backend/app/agents/leader.py  — line 343-359 (LeaderDecision 생성 부분)
```

### 세부 작업

`leader.py`의 LeaderDecision 생성 코드 수정:

```python
# 기존 run() 메서드에서 ltm_history 로드 시 ltm_turns 계산
ltm_turns = len(ltm_history) if ltm_history else 0

# CONCEPT_DETECTED 이벤트에서 이미 구분된 값을 사용
# all_concepts 생성 시점에 detected(직접)와 expanded(확장) 분리 저장
direct_concept_ids = detected          # line 159에서 생성
expanded_concept_ids = [c for c in all_concepts if c not in detected_set]

# LeaderDecision 저장 시 신규 필드 추가
db.add(LeaderDecision(
    request_id=request_id,
    detected_intent=intent_data.get("intent"),
    detected_concepts=all_concepts,
    direct_concepts=direct_concept_ids,           # 추가
    expanded_concepts=expanded_concept_ids,       # 추가
    selected_agents=routed_agents,
    reasoning=intent_data,
    confidence_score=confidence,
    total_steps=len(steps),
    memory_turns=memory_turns,
    ltm_turns=ltm_turns,                          # 추가
    answer=answer,                                # 추가
    # review_reason은 Phase 5에서 추가
))
```

### Evidence 저장 시 agent_id 추가

`leader.py:280-289`의 `save_evidence_with_score()` 호출에 `agent_id` 추가:

```python
_save_ev(
    db=db,
    request_id=request_id,
    concept_id=api_to_concept.get(api_res["api_id"]),
    source_id=api_res["api_id"],
    content=api_res["data"],
    intent=intent_str,
    response_latency_ms=api_res.get("latency_ms", per_api_latency),
    agent_id=route_item.agent_id,    # 추가
)
```

`evidence_service.py`의 `save_evidence_with_score()` 함수에 `agent_id` 파라미터 추가 후 저장.

### 완료 기준
- 채팅 요청 후 `leader_decision.answer`, `direct_concepts`, `expanded_concepts`, `ltm_turns` 값 확인
- `evidence_reference.agent_id` 값 확인

### 테스트 방법
```bash
POST /api/v1/ai/chat
→ DB: SELECT answer, direct_concepts, expanded_concepts FROM leader_decision ORDER BY id DESC LIMIT 1;
→ DB: SELECT agent_id FROM evidence_reference ORDER BY id DESC LIMIT 5;
```

### 금지 사항
- `leader.py`의 기존 처리 흐름 변경 없음
- 기존 LeaderDecision 필드 제거 없음

---

## Phase 5. Backend — Score 분해 + review_reason 계산 로직

### 목표
`leader_evaluation.py`에 `ScoreBreakdown`과 `review_reason` 계산 로직을 추가한다.

### 수정 대상 파일
```
backend/app/api/routes/leader_evaluation.py
backend/app/schemas/leader_evaluation.py
```

### 세부 작업

**1. 스키마 추가 (`leader_evaluation.py`)**

```python
class ScoreBreakdown(BaseModel):
    intent_score: float | None
    concept_score: float | None
    routing_score: float | None
    tool_success_score: float | None
    evidence_score: float | None
    final_score: float | None
```

기존 스키마에 필드 추가:
- `LeaderEvaluationListItemResponse` — `review_reason`, `score_breakdown`, `direct_concepts`, `expanded_concepts`, `unrouted_concepts`
- `LeaderDecisionResponse` — `direct_concepts`, `expanded_concepts`, `unrouted_concepts`, `concept_agent_mappings`, `intent_keywords`, `intent_urgency`, `ltm_turns`, `review_reason`
- `EvidenceSummaryResponse` — `missing_concepts`, `grounding_score`, `review_flags`
- `LeaderEvaluationDetailResponse` — `answer`

**2. 계산 함수 추가 (`leader_evaluation.py`)**

`_compute_score_breakdown()` 함수:

```python
def _compute_score_breakdown(
    decision: LeaderDecision | None,
    evidences: list[EvidenceReference],
    unrouted_concepts: list[str],
    all_concepts: list[str],
) -> ScoreBreakdown:
    intent_score = 1.0 if (decision and decision.detected_intent not in [None, "OTHER"]) else 0.5
    
    total_c = len(all_concepts)
    unrouted_c = len(unrouted_concepts)
    concept_score = 1.0 if total_c == 0 else round((total_c - unrouted_c) / total_c, 4)
    routing_score = concept_score  # 현재 동일 기준
    
    tool_success_score = decision.confidence_score if decision else None
    evidence_score = _avg([ev.confidence_score for ev in evidences])
    
    if all(v is not None for v in [intent_score, concept_score, routing_score, tool_success_score, evidence_score]):
        final_score = round(
            intent_score * 0.15 + concept_score * 0.20 + routing_score * 0.15
            + tool_success_score * 0.25 + evidence_score * 0.25,
            4,
        )
    else:
        final_score = tool_success_score  # 최소한 tool 성공률
    
    return ScoreBreakdown(
        intent_score=intent_score,
        concept_score=concept_score,
        routing_score=routing_score,
        tool_success_score=tool_success_score,
        evidence_score=evidence_score,
        final_score=final_score,
    )
```

`_infer_review_reason()` 함수 추가 (IMPROVEMENT_DESIGN.md 설계 기준).

`_infer_overall_result()` 함수 개선 (BLOCKED 추가, evidence_count=0 → FAIL).

**3. `_extract_unrouted_concepts()` 헬퍼**

AGENT_SELECTED 이벤트의 `output_data.unrouted_concepts`에서 추출:

```python
def _extract_unrouted_concepts(events: list[TraceEvent]) -> list[str]:
    event = _find_first_event(events, "AGENT_SELECTED")
    if event and event.output_data:
        return event.output_data.get("unrouted_concepts", [])
    return []
```

### 완료 기준
- `GET /api/v1/admin/leader-evaluations` 응답에 `review_reason`, `score_breakdown` 포함
- `GET /api/v1/admin/leader-evaluations/{id}` 응답에 `answer`, `direct_concepts`, `unrouted_concepts`, `score_breakdown` 포함
- BLOCKED 케이스(빈 DB 상태) 확인

### 테스트 방법
```bash
GET /api/v1/admin/leader-evaluations
→ 첫 번째 item의 review_reason, score_breakdown 확인
GET /api/v1/admin/leader-evaluations/{id}
→ answer, direct_concepts, unrouted_concepts, score_breakdown 확인
```

### 금지 사항
- 기존 `confidence_score` 필드 제거/변경 없음
- 기존 API 응답 필드 제거 없음

---

## Phase 6. Backend — Evidence Summary + Grounding Score

### 목표
Evidence Summary에 `missing_concepts`, `grounding_score`, `review_flags`를 추가한다.

### 수정 대상 파일
```
backend/app/api/routes/leader_evaluation.py
backend/app/schemas/leader_evaluation.py
```

### 세부 작업

`_build_evidence_summary()` 함수 확장:

```python
def _build_evidence_summary(
    evidences: list[EvidenceReference],
    all_concepts: list[str],
    answer_length: int,
) -> EvidenceSummaryResponse:
    evidence_concepts = {ev.concept_id for ev in evidences if ev.concept_id}
    missing = [c for c in all_concepts if c not in evidence_concepts]
    
    avg_conf = _avg([ev.confidence_score for ev in evidences])
    grounding = _compute_grounding_score(
        evidence_count=len(evidences),
        avg_evidence_confidence=avg_conf,
        answer_length=answer_length,
        missing_concepts_count=len(missing),
    )
    
    flags = []
    if len(evidences) == 0:
        flags.append("EVIDENCE_MISSING")
    if avg_conf is not None and avg_conf < 0.60:
        flags.append("EVIDENCE_LOW_QUALITY")
    if missing:
        flags.append(f"MISSING_CONCEPTS: {', '.join(missing[:3])}")
    if grounding is not None and grounding < 0.60:
        flags.append("GROUNDING_WEAK")
    
    return EvidenceSummaryResponse(
        evidence_count=len(evidences),
        avg_evidence_confidence=avg_conf,
        avg_data_quality_score=_avg([ev.data_quality_score for ev in evidences]),
        avg_intent_relevance_score=_avg([ev.intent_relevance_score for ev in evidences]),
        missing_concepts=missing,
        grounding_score=grounding,
        review_flags=flags,
    )
```

### 완료 기준
- API 응답의 `evidence_summary.missing_concepts` 값 확인
- `grounding_score` 값 존재 확인
- `review_flags` 목록 확인

### 금지 사항
- `grounding_score`는 추정값임을 코드 주석으로 명시

---

## Phase 7. Backend — LeaderEvaluationEvidence에 agent_id + content_preview 추가

### 목표
Evidence 그리드에 agent_id와 content 미리보기를 추가한다.

### 수정 대상 파일
```
backend/app/schemas/leader_evaluation.py
backend/app/api/routes/leader_evaluation.py
```

### 세부 작업

`LeaderEvaluationEvidenceResponse`에 필드 추가:

```python
agent_id: str | None          # EvidenceReference.agent_id
content_preview: dict | None  # content의 상위 키 + 값 미리보기 (운영자용)
```

`_serialize_evidence()` 수정:

```python
def _serialize_evidence(ev: EvidenceReference) -> LeaderEvaluationEvidenceResponse:
    preview = None
    if ev.content and isinstance(ev.content, dict):
        # 목록 응답이면 첫 번째 항목만, 단건 응답이면 전체
        for list_key in ["products", "rates", "policies", "documents", "branches", "histories"]:
            if list_key in ev.content:
                items = ev.content[list_key]
                preview = {list_key: items[:1] if items else []}
                break
        if preview is None:
            preview = {k: v for k, v in list(ev.content.items())[:3]}  # 앞 3개 키
    
    return LeaderEvaluationEvidenceResponse(
        ...existing fields...,
        agent_id=ev.agent_id,
        content_preview=preview,
    )
```

### 완료 기준
- Evidence 응답에 `agent_id`, `content_preview` 포함 확인

---

## Phase 8. Frontend — 타입 확장

### 목표
Phase 2~7의 Backend 변경에 맞춰 프론트 타입을 업데이트한다.

### 수정 대상 파일
```
frontend/src/types/leaderEvaluation.ts
```

### 세부 작업

```typescript
// 추가
export type ScoreBreakdown = {
  intent_score: number | null;
  concept_score: number | null;
  routing_score: number | null;
  tool_success_score: number | null;
  evidence_score: number | null;
  final_score: number | null;
};

// LeaderEvaluationListItem 확장
review_reason: string | null;
score_breakdown: ScoreBreakdown | null;
direct_concepts: string[];
expanded_concepts: string[];
unrouted_concepts: string[];
tool_success_count: number;
tool_failed_count: number;
intent_keywords: string[];

// LeaderDecisionDetail 확장
direct_concepts: string[];
expanded_concepts: string[];
unrouted_concepts: string[];
intent_keywords: string[];
intent_urgency: string | null;
ltm_turns: number;
review_reason: string | null;

// LeaderEvaluationEvidenceSummary 확장
missing_concepts: string[];
grounding_score: number | null;
review_flags: string[];

// LeaderEvaluationDetail 확장
answer: string | null;

// LeaderEvaluationEvidence 확장
agent_id: string | null;
content_preview: Record<string, unknown> | null;
```

### 완료 기준
- TypeScript 컴파일 오류 없음 (`npm run build` 또는 `/type-check`)

---

## Phase 9. Frontend — 리더 평가 목록 개선

### 목표
상단 목록 컬럼을 IMPROVEMENT_DESIGN.md 설계 기준으로 개선한다.

### 수정 대상 파일
```
frontend/src/app/admin/leader-evaluations/page.tsx
```

### 세부 작업

**1. 목록 컬럼 재정의**

```typescript
const listColumns: GridColDef[] = [
  {
    field: "user_question",
    headerName: "질문",
    minWidth: 200,
    flex: 1.2,
    renderCell: (params) => (
      <Tooltip title={params.value ?? ""}>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {params.value ? String(params.value).slice(0, 50) + (String(params.value).length > 50 ? "…" : "") : "-"}
        </span>
      </Tooltip>
    ),
  },
  {
    field: "detected_intent",
    headerName: "Intent",
    width: 130,
    renderCell: (params) => <IntentChip intent={params.value} />,
  },
  { field: "concept_count", headerName: "Concepts", width: 90 },
  {
    field: "selected_agents",
    headerName: "Agents",
    minWidth: 200,
    flex: 0.9,
    renderCell: (params) => <AgentChips agents={params.value} />,
  },
  { field: "evidence_count_display", headerName: "Evidence", width: 100 },
  { field: "final_score", headerName: "Score", width: 90 },
  {
    field: "overall_result",
    headerName: "Status",
    width: 120,
    renderCell: (params) => <ResultChip result={params.value} />,
  },
  {
    field: "review_reason",
    headerName: "원인",
    minWidth: 160,
    flex: 0.8,
    renderCell: (params) => <ReviewReasonText code={params.value} />,
  },
];
```

**2. 헬퍼 컴포넌트 (page.tsx 내부 또는 별도 파일)**

- `IntentChip`: intent별 색상 Chip
- `ResultChip`: PASS=green, NEEDS_REVIEW=amber, FAIL=red, BLOCKED=grey
- `ReviewReasonText`: 코드 → 한글 메시지 변환
- `AgentChips`: agent 배열 → Chip 목록 (2개 초과 시 `+N`)

**3. listRows 변환 수정**

```typescript
const listRows = useMemo(
  () =>
    (listQuery.data?.items ?? []).map((item) => ({
      id: item.request_id,
      ...item,
      concept_count: `${item.detected_concepts.length}개`,
      evidence_count_display: `${item.avg_evidence_confidence != null ? item.avg_evidence_confidence.toFixed(2) : "-"}`,
      final_score: item.score_breakdown?.final_score?.toFixed(3) ?? item.leader_confidence_score?.toFixed(3) ?? "-",
    })),
  [listQuery.data]
);
```

### 완료 기준
- 목록에서 Intent Chip 색상 표시 확인
- Status Chip 색상 표시 확인
- 원인 한글 메시지 표시 확인
- 긴 질문 말줄임 + tooltip 동작 확인

---

## Phase 10. Frontend — 리더 판단 상세 패널 개선

### 목표
요약 카드(우측 패널)와 "리더 판단" 섹션을 IMPROVEMENT_DESIGN.md 설계 기준으로 개선한다.

### 수정 대상 파일
```
frontend/src/app/admin/leader-evaluations/page.tsx
```

### 세부 작업

**요약 카드 개선:**
- `answer` 표시 (null이면 안내 메시지)
- `score_breakdown` 막대 차트 (간단한 progress bar)
- `review_reason` 한글 메시지

**리더 판단 패널 개선:**
- `intent_keywords` / `intent_urgency` Chip 표시
- `memory_turns` / `ltm_turns` 표시
- `detected_concepts` → `direct_concepts` / `expanded_concepts` 구분 표시
  - 직접 탐지: 파란색 Chip
  - 확장 추가: 회색 Chip (온톨로지)
- `unrouted_concepts` 경고 색상 Chip
- concept→agent 매핑 목록 (TraceEvent AGENT_SELECTED output_data 파싱)
- Score Breakdown 진행 바

**상세 로딩 인디케이터 추가:**

```typescript
{detailQuery.isLoading && <LinearProgress sx={{ mb: 1 }} />}
```

### 완료 기준
- direct_concepts / expanded_concepts 구분 표시 확인
- unrouted_concepts 경고 표시 확인
- score_breakdown 진행 바 표시 확인
- answer 텍스트 표시 확인

---

## Phase 11. Frontend — Evidence Summary / Detail 개선

### 목표
Evidence Summary 카드와 Evidence 그리드를 개선한다.

### 수정 대상 파일
```
frontend/src/app/admin/leader-evaluations/page.tsx
```

### 세부 작업

**Evidence Summary 카드:**
- `evidence_count` 총/성공/실패 표시
- 점수 3개 progress bar 표시
- `missing_concepts` 경고 Chip 목록
- `review_flags` 목록
- `grounding_score` 표시 (추정값 안내)

**Evidence 그리드 컬럼 추가:**

```typescript
const evidenceColumns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 70 },
  { field: "concept_short", headerName: "Concept", minWidth: 160, flex: 1 },
  { field: "agent_id", headerName: "Agent", width: 130 },
  { field: "source_id", headerName: "Source", minWidth: 160, flex: 0.8 },
  { field: "confidence_score", headerName: "Conf", width: 90 },
  { field: "data_quality_score", headerName: "Quality", width: 90 },
  { field: "intent_relevance_score", headerName: "Intent", width: 90 },
  { field: "item_count", headerName: "Items", width: 70 },
  {
    field: "expand",
    headerName: "상세",
    width: 80,
    renderCell: (params) => <ExpandButton row={params.row} />,
  },
];
```

Evidence 행 선택/확장 시 quality_flags + content_preview JSON 펼침 표시.

**evidenceRows 변환:**
```typescript
const evidenceRows = (detail?.evidences ?? []).map(ev => ({
  ...ev,
  concept_short: (ev.concept_id ?? "").replace("CONCEPT_", ""),
}));
```

### 완료 기준
- agent_id 컬럼 표시 확인
- quality_flags 펼침 확인
- missing_concepts 경고 표시 확인

---

## Phase 12. Frontend — Trace Timeline 개선

### 목표
Trace Events 그리드를 타임라인 형태 컴포넌트로 교체한다.

### 수정 대상 파일
```
frontend/src/app/admin/leader-evaluations/page.tsx
(또는 frontend/src/components/trace/TraceTimeline.tsx 신규)
```

### 세부 작업

**`TraceTimeline` 컴포넌트 구현:**

```typescript
// 표시 항목: 아이콘 + event_type + duration_ms + 요약 1줄
// duration_ms > 1000ms: 주황 하이라이트
// duration_ms > 5000ms: 빨간 하이라이트 (타임아웃 가능성)
// status !== "success": ❌ 아이콘

interface TraceTimelineProps {
  events: LeaderEvaluationTraceEvent[];
}
```

이벤트별 요약 함수 `summarizeEvent()` 구현 (IMPROVEMENT_DESIGN.md 설계 기준).

**TOOL_INVOKED 이벤트:**
- `input_data.api_id` 표시 (tool_id가 이제 채워지므로 우선 tool_id 사용)
- `input_data.agent_id` 표시
- duration_ms + 색상 하이라이트

**이벤트 클릭 시 JSON 열람:**
- 클릭 → `input_data`/`output_data` 전체 JSON을 모달 또는 사이드 패널로 표시

**빈 상태 처리:**
```typescript
if (!events.length) {
  return (
    <Alert severity="warning">
      Trace 데이터가 없습니다. 마이그레이션 상태 또는 요청 처리 오류를 확인하세요.
    </Alert>
  );
}
```

### 완료 기준
- 11개 이벤트 순서대로 표시 확인
- TOOL_INVOKED에 api_id 표시 확인
- 고지연 이벤트 색상 하이라이트 확인
- JSON 열람 동작 확인

---

## Phase 13. Frontend — Empty State / Error State / Loading State 개선

### 목표
데이터 없음 / 오류 / 로딩 상태의 사용자 경험을 개선한다.

### 수정 대상 파일
```
frontend/src/app/admin/leader-evaluations/page.tsx
```

### 세부 작업

| 케이스 | 현재 | 개선 후 |
|---|---|---|
| 목록 로딩 중 | 빈 그리드 | LinearProgress + skeleton |
| 목록 없음 | 빈 그리드 | "조회 결과가 없습니다. Request ID 검색어를 확인하세요." |
| 상세 로딩 중 | 변화 없음 | LinearProgress 표시 |
| 상세 오류 | Alert | 오류 종류별 안내 메시지 |
| Trace 없음 | 빈 그리드 | 원인 추정 안내 Alert |
| Evidence 없음 | 빈 그리드 | 원인 추정 안내 Alert |
| BLOCKED status | 없음 | 회색 배경 + "시스템 오류" 안내 |

### 완료 기준
- Mock API 중단 상태에서 Evidence 없음 안내 표시 확인
- 인증 오류 시 적절한 메시지 표시 확인
- 로딩 중 인디케이터 표시 확인

---

## Phase 14. 통합 테스트 및 검증

### 목표
전체 개선 사항을 시나리오 기반으로 검증한다.

### 세부 작업

**시나리오 1: 정상 처리 (PASS)**
```
질문: "신용대출 금리 알려줘"
기대: Intent=INQUIRY, Concepts 탐지, Agent 선택, Evidence 2건 이상, PASS
확인: score_breakdown.final_score > 0.80
```

**시나리오 2: Tool 실패 (FAIL)**
```
Mock API 중단 후 요청
기대: TOOL_INVOKED 실패, Evidence 0건, FAIL, review_reason=TOOL_FAILED
```

**시나리오 3: Concept 미탐지 (NEEDS_REVIEW)**
```
질문: "안녕하세요"
기대: INQUIRY, concept 미탐지 또는 unrouted, NEEDS_REVIEW
```

**시나리오 4: LTM 활용**
```
session_id 동일로 2번 요청
기대: 두 번째 요청에 ltm_turns > 0
```

**시나리오 5: 화면 연결 검증**
```
Swagger → /api/v1/ai/chat 실행
→ 리더 평가 목록에서 해당 request_id 확인
→ row 선택 → 상세 패널 로딩 확인
→ Trace Timeline 11개 이벤트 확인
→ Evidence 그리드 데이터 확인
```

### 완료 기준
- 5개 시나리오 모두 예상대로 동작
- `pytest` 전체 통과 (기존 테스트 회귀 없음)
- TypeScript 빌드 오류 없음

### 리스크
- 기존 `test_chat.py` 케이스가 LeaderDecision 필드 변경으로 실패할 수 있음 → Phase 4 완료 후 먼저 pytest 실행

---

## 전체 Phase 의존성 순서

```
Phase 1 (분석 확인)
  └─ Phase 2 (tool_id 수정)
      └─ Phase 3 (DB 컬럼 추가 + Migration)
          └─ Phase 4 (LeaderDecision 저장 확장)
              └─ Phase 5 (Score 분해 + review_reason)
                  └─ Phase 6 (Evidence Summary)
                      └─ Phase 7 (Evidence agent_id)
                          └─ Phase 8 (Frontend 타입 확장)
                              ├─ Phase 9 (목록 개선)
                              ├─ Phase 10 (상세 패널 개선)
                              ├─ Phase 11 (Evidence 개선)
                              └─ Phase 12 (Trace Timeline)
                                  └─ Phase 13 (Empty/Error State)
                                      └─ Phase 14 (통합 테스트)
```

---

## 구현 전 반드시 확인 사항

1. `record_event()` 함수 시그니처 — `agent_id`, `tool_id` 파라미터 존재 여부
2. `save_evidence_with_score()` 함수 시그니처 — `agent_id` 파라미터 추가 가능 여부
3. `alembic/env.py`에 `trace_model` import 확인 — autogenerate 대상 포함 여부
4. 기존 `pytest` 전체 실행 후 현재 상태 기록 (Phase 4 후 회귀 비교용)
5. Docker 컨테이너 상태 확인 (`docker compose ps`)

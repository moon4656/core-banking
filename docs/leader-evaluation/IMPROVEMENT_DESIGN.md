# 리더 평가 화면 — 개선 설계 (IMPROVEMENT_DESIGN)

> 이 문서는 `CURRENT_ANALYSIS.md`를 기반으로 개선 방향을 설계한다.  
> 코드 수정은 `IMPLEMENTATION_TASKS.md`의 Phase별 승인 후 시작한다.

---

## 1. 개선 목표

Leader Agent가 왜 그런 판단을 했는지 설명 가능해야 한다.

```
Intent → Concept → Agent → Tool → Evidence → Answer
```

이 흐름이 request_id 기준으로 추적 가능해야 한다.  
PASS / NEEDS_REVIEW / FAIL 상태가 근거와 함께 설명 가능해야 한다.  
운영자, 개발자, QA가 각자 필요한 관점으로 리더 평가를 확인할 수 있어야 한다.

---

## 2. 사용자 유형별 목표

### 운영자
- NEEDS_REVIEW/FAIL의 직접 원인을 한 줄(`review_reason`)로 확인
- 최종 답변 텍스트 확인 (answer)
- 성공/실패 API 수와 Evidence 품질 수준 빠르게 파악
- 사람이 재검토해야 하는지 즉시 판단

### 개발자
- Intent 분석부터 Answer 생성까지 단계별 latency 확인
- 어떤 API가 실패했는지, 어떤 concept이 미매핑됐는지 파악
- Evidence quality_flags 등 세부 품질 데이터 확인
- TraceEvent에서 tool_id, agent_id 직접 확인
- 원본 API 응답(content) 열람

### QA
- 직접 탐지 concept vs 온톨로지 확장 concept 구분 확인
- unrouted_concepts (매핑 없는 concept) 확인
- keywords, urgency 등 Intent 판단 근거 확인
- score 분해 (intent/concept/routing/tool/evidence 개별 점수)
- 회귀 테스트 기준으로 PASS/FAIL 기준 일관성 확인

---

## 3. 변경 대상 파일 목록

### Backend
```
backend/app/models/trace_model.py            — DB 컬럼 추가 (LeaderDecision, EvidenceReference)
backend/app/agents/leader.py                 — LeaderDecision 저장 시 answer 추가, tool_id 수정
backend/app/api/routes/leader_evaluation.py  — score 분해, review_reason, answer 포함
backend/app/schemas/leader_evaluation.py     — 응답 스키마 확장
```

### Alembic (Migration)
```
backend/alembic/versions/xxxx_add_leader_eval_fields.py
```

### Frontend
```
frontend/src/app/admin/leader-evaluations/page.tsx  — 화면 전체 개선
frontend/src/types/leaderEvaluation.ts              — 타입 확장
```

---

## 4. DB 변경 필요 여부 및 내용

### `leader_decision` 테이블 — 추가 컬럼

| 컬럼 | 타입 | 설명 | nullable |
|---|---|---|---|
| `answer` | Text | 최종 LLM 답변 | nullable |
| `direct_concepts` | JSON | 직접 탐지된 concept 목록 | nullable |
| `expanded_concepts` | JSON | 온톨로지 확장으로 추가된 concept | nullable |
| `review_reason` | String(100) | NEEDS_REVIEW/FAIL 원인 코드 | nullable |
| `ltm_turns` | Integer | 활용된 LTM 턴 수 | nullable |

> `detected_concepts`는 기존 컬럼 유지 (직접+확장 전체 목록). `direct_concepts`/`expanded_concepts`를 별도 추가.

### `evidence_reference` 테이블 — 추가 컬럼

| 컬럼 | 타입 | 설명 | nullable |
|---|---|---|---|
| `agent_id` | String(100) | Evidence를 생성한 Agent ID | nullable |

### 변경 없는 테이블
- `trace_event`: 컬럼 추가 없음. `tool_id` 저장 방식만 코드에서 수정.
- 기존 컬럼 타입/삭제 없음 → 기존 데이터 호환 유지.

---

## 5. Alembic Migration 필요 여부

필요. `alembic revision --autogenerate`로 자동 생성 가능.  
새 컬럼은 모두 nullable이므로 기존 레코드에 영향 없음.

---

## 6. API 변경 설계

### 기존 API 유지 (Breaking Change 없음)

기존 `GET /api/v1/admin/leader-evaluations` / `GET /api/v1/admin/leader-evaluations/{id}` 경로·응답 구조 유지.  
**응답 필드 추가만 허용** — 기존 클라이언트가 새 필드를 무시하면 되므로 하위 호환.

### 응답 스키마 확장

#### `LeaderEvaluationListItemResponse` 추가 필드

```python
answer: str | None                     # 최종 답변 (앞 100자 preview)
review_reason: str | None              # NEEDS_REVIEW/FAIL 원인 코드
direct_concepts: list[str]             # 직접 탐지 concept
expanded_concepts: list[str]           # 확장 추가 concept
unrouted_concepts: list[str]           # 매핑 없는 concept (AGENT_SELECTED 이벤트 파싱)
tool_success_count: int                # 성공 Tool 수
tool_failed_count: int                 # 실패 Tool 수
intent_keywords: list[str]             # keywords (reasoning JSON 파싱)
score_breakdown: ScoreBreakdown | None # 점수 분해
```

#### `LeaderDecisionResponse` 추가 필드

```python
direct_concepts: list[str]             # 직접 탐지
expanded_concepts: list[str]           # 확장 추가
unrouted_concepts: list[str]           # 미매핑 concept
concept_agent_mappings: list[ConceptAgentMapping]  # concept→agent 매핑 이유
intent_keywords: list[str]
intent_urgency: str | None
answer: str | None
ltm_turns: int
review_reason: str | None
```

#### `EvidenceSummaryResponse` 추가 필드

```python
missing_concepts: list[str]            # evidence 없는 concept
grounding_score: float | None          # 답변-evidence 연결 점수 (추정값)
review_flags: list[str]                # 주요 문제 목록
```

#### `LeaderEvaluationEvidenceResponse` 추가 필드

```python
agent_id: str | None                   # evidence 생성 Agent
content_preview: dict | None           # content 앞부분 (운영자용 요약)
```

#### 새 스키마 — `ScoreBreakdown`

```python
class ScoreBreakdown(BaseModel):
    intent_score: float | None         # 의도 판단 적합도
    concept_score: float | None        # concept 탐지 품질
    routing_score: float | None        # agent 선택 적합도
    tool_success_score: float          # tool 성공률 (= leader_confidence_score)
    evidence_score: float | None       # 평균 evidence confidence
    final_score: float | None          # 종합 점수
```

> `final_score`는 별도 계산. 기존 `leader_confidence_score`(Tool 성공률) 의미 변경 없음.

---

## 7. review_reason 생성 방식 설계

`_infer_review_reason()` 함수를 `leader_evaluation.py`에 추가.  
우선순위 순서로 단 하나의 reason 코드를 반환한다.

```python
def _infer_review_reason(
    failed_step_count: int,
    leader_confidence: float | None,
    evidence_count: int,
    avg_evidence_confidence: float | None,
    unrouted_concepts: list[str],
) -> str | None:
    if leader_confidence is None and evidence_count == 0:
        return "SYSTEM_BLOCKED"         # 데이터 자체가 없음
    if failed_step_count > 0 and leader_confidence is not None and leader_confidence < 0.5:
        return "TOOL_FAILED"
    if not unrouted_concepts and leader_confidence is None:
        return "CONCEPT_MISSING"
    if len(unrouted_concepts) > 0:
        return "AGENT_ROUTING_WEAK"
    if evidence_count == 0:
        return "EVIDENCE_MISSING"
    if avg_evidence_confidence is not None and avg_evidence_confidence < 0.60:
        return "EVIDENCE_LOW_QUALITY"
    if avg_evidence_confidence is not None and avg_evidence_confidence < 0.75:
        return "GROUNDING_WEAK"
    return None  # PASS
```

**review_reason 코드 → 사용자 표시 메시지 매핑 (프론트에서 변환):**

| 코드 | 운영자용 메시지 |
|---|---|
| `SYSTEM_BLOCKED` | 시스템 오류로 처리 불가 |
| `TOOL_FAILED` | API 호출 실패 — 데이터 부족 |
| `CONCEPT_MISSING` | 질문에서 관련 개념을 탐지하지 못함 |
| `AGENT_ROUTING_WEAK` | 일부 개념에 담당 Agent 없음 |
| `EVIDENCE_MISSING` | 근거 데이터 없음 |
| `EVIDENCE_LOW_QUALITY` | 근거 데이터 품질 낮음 |
| `GROUNDING_WEAK` | 답변과 근거 연결이 약함 |
| `null` | 이상 없음 (PASS) |

---

## 8. Status 기준 개선 설계

현재 로직을 확장. 기존 PASS/NEEDS_REVIEW/FAIL 범주 유지, BLOCKED 추가.

```python
def _infer_overall_result(...) -> str:
    # BLOCKED: 데이터 자체가 없거나 처리 전체 실패
    if leader_confidence is None and evidence_count == 0 and trace_event_count <= 1:
        return "BLOCKED"
    # FAIL: 심각한 실패 조건
    if failed_step_count > 0 or (leader_confidence is not None and leader_confidence < 0.5):
        return "FAIL"
    if evidence_count == 0:
        return "FAIL"
    # NEEDS_REVIEW: 품질 문제
    if avg_evidence_confidence is not None and avg_evidence_confidence < 0.75:
        return "NEEDS_REVIEW"
    if unrouted_concepts:
        return "NEEDS_REVIEW"
    return "PASS"
```

**개선된 기준표:**

| Status | 조건 |
|---|---|
| BLOCKED | trace_event 1건 이하 AND evidence 0건 AND leader_confidence null |
| FAIL | failed_step_count > 0 OR leader_confidence < 0.5 OR evidence_count = 0 |
| NEEDS_REVIEW | avg_evidence_confidence < 0.75 OR unrouted_concepts 있음 |
| PASS | 나머지 |

---

## 9. Score 분해 방식 설계

기존 `confidence_score`(Tool 성공률)는 `tool_success_score`로 별칭 제공. 변경 없음.  
새 `ScoreBreakdown`을 API 응답에 추가.

```
tool_success_score    = leader_confidence_score (기존값 그대로)
evidence_score        = avg_evidence_confidence (기존값 그대로)
intent_score          = 1.0 if detected_intent not in [None, "OTHER"] else 0.5
concept_score         = detected_concepts_count / max(1, detected_concepts_count + unrouted_concepts_count)
routing_score         = 1.0 - (unrouted_concepts_count / max(1, total_concepts_count))
final_score           = (intent_score × 0.15 + concept_score × 0.20 + routing_score × 0.15
                        + tool_success_score × 0.25 + evidence_score × 0.25)
```

> 이 공식은 추정 기반 계산이며, 실제 값 검증 후 가중치 조정 필요.  
> QA가 예상 Intent/Concept과 비교 기능을 추가하면 `intent_score`를 실측값으로 교체 가능.

---

## 10. 상단 목록 컬럼 설계

기존 7컬럼에서 다음으로 개선.

| 컬럼 | 필드 | 표시 방식 |
|---|---|---|
| 질문 | `user_question` | 50자 이상 말줄임 + tooltip |
| Intent | `detected_intent` | 색상 Chip (INQUIRY=blue, COMPARISON=purple, RECOMMENDATION=green, APPLICATION=orange) |
| Concepts | `detected_concepts.length` | 숫자만 표시 (예: "4개"), hover 시 목록 tooltip |
| Agents | `selected_agents` | Chip 목록 (2개 이상이면 "+N" 더보기) |
| Evidence | `avg_evidence_confidence` | 소수점 2자리 + 레벨 바 (0~1) |
| Score | `final_score` | 소수점 2자리 |
| Status | `overall_result` | 색상 Chip (PASS=green, NEEDS_REVIEW=yellow, FAIL=red, BLOCKED=gray) |
| 원인 | `review_reason` | 짧은 한글 메시지 (null이면 "-") |

> `leader_confidence_score` 컬럼 제거 (중복). `final_score` 상세 내역은 선택 시 우측 패널에서 표시.

---

## 11. 리더 판단 상세 패널 설계

row 선택 시 우측 패널 (현재 요약 카드 확장).

```
리더 판단 상세

질문:
  [user_question]

Intent: [detected_intent chip]
Keywords: [keyword chips]
Urgency: [urgency chip]

Short Memory 활용: [memory_turns]턴
Long-term Memory 활용: [ltm_turns]턴

━━━━━━━━━━━━━━━━
Concept 탐지
  직접 탐지: [direct_concepts chips]
  확장 추가: [expanded_concepts chips]
  매핑 없음: [unrouted_concepts chips — warning 색상]

━━━━━━━━━━━━━━━━
Agent 라우팅
  [concept → agent 매핑 목록]
  예: CONCEPT_INTEREST_RATE → RATE_AGENT

━━━━━━━━━━━━━━━━
Score Breakdown
  Intent:   [intent_score]   ████░░
  Concept:  [concept_score]  ████░░
  Routing:  [routing_score]  ███░░░
  Tool:     [tool_success]   █████░
  Evidence: [evidence_score] ███░░░
  Final:    [final_score]    ████░░

Status: [NEEDS_REVIEW chip]
원인:   [review_reason 메시지]
```

---

## 12. Evidence Summary 설계

현재 Evidence Summary 카드 개선.

```
Evidence Summary

총 근거: [N]건  |  성공: [N]건  |  실패: [N]건

평균 Confidence:      [0.74] ████░░░░░░
평균 Data Quality:    [0.68] ██████░░░░
평균 Intent Fit:      [0.80] ████████░░

━━━━━━━━━━━━━━━━
Missing Evidence (Evidence 없는 Concept):
  [concept chips — warning 색상]

Related Evidence:
  [linked pairs 목록] 예: LOAN ↔ RATE (연결됨)
  [missing links]     예: DOCUMENT Evidence 없음

Score Breakdown: Evidence [0.62]

주요 문제:
  [review_flags 목록]
```

---

## 13. Evidence Detail 설계

Evidence 그리드에 컬럼 추가.

| 컬럼 | 내용 | 표시 |
|---|---|---|
| ID | evidence id | 숫자 |
| Concept | concept_id | 짧게 (CONCEPT_ 제거) |
| Agent | agent_id | Chip |
| Source | source_id | Chip |
| Confidence | confidence_score | 소수점 2자리 |
| Quality | data_quality_score | 소수점 2자리 |
| Intent Fit | intent_relevance_score | 소수점 2자리 |
| Items | item_count | 숫자 |
| Related | related_evidence_ids.length | 숫자 (hover 시 ID 목록) |
| 상세 | expand 버튼 | quality_flags + content_preview 펼침 |

> content(원본 JSON)는 기본 숨김, 개발자용 "원본 보기" 토글로 펼침.

---

## 14. Trace Timeline 설계

현재 단순 테이블 → 타임라인 형태로 개선.

**표시 형식:**

```
Trace Timeline

✅ REQUEST_RECEIVED       [12ms]   — 요청 수신
✅ MEMORY_LOADED          [8ms]    — Short Memory 로드 (3턴)
✅ LTM_LOADED             [14ms]   — Long-term Memory 로드 (2턴)
✅ INTENT_ANALYZED        [420ms]  — INQUIRY / ["신용대출", "금리"]
✅ CONCEPT_DETECTED       [33ms]   — 직접 3개, 확장 2개
✅ AGENT_SELECTED         [21ms]   — RATE_AGENT, PRODUCT_AGENT
✅ TOOL_INVOKED           [180ms]  MOCK_PRODUCT_LOOKUP (PRODUCT_AGENT)
✅ TOOL_INVOKED           [210ms]  MOCK_RATE_LOOKUP (RATE_AGENT)
✅ PLAN_CREATED           [12ms]   — step 2건
✅ RESULTS_RERANKED       [5ms]    — 성공 2건
✅ RESPONSE_COMPLETED     [900ms]  — 답변 218자
```

**실패 이벤트:**

```
❌ TOOL_INVOKED           [10000ms]  MOCK_RATE_LOOKUP — timeout
```

**구현 방식:**
- 기존 `BaseDataGrid` 대신 커스텀 `TraceTimeline` 컴포넌트 사용
- `duration_ms`가 임계값(1000ms) 초과 시 주황/빨강 하이라이트
- `input_data`/`output_data`를 파싱해 각 이벤트별 요약 1줄 생성
- 이벤트 클릭 시 JSON 전체 열람 가능 (개발자용)

**이벤트별 요약 문구 생성 로직:**

```typescript
function summarizeEvent(event: TraceEvent): string {
  switch (event.event_type) {
    case "MEMORY_LOADED":    return `Short Memory ${event.output_data?.turns_loaded ?? 0}턴`;
    case "LTM_LOADED":       return `LTM ${event.output_data?.ltm_turns_loaded ?? 0}턴`;
    case "INTENT_ANALYZED":  return `${event.output_data?.intent} / [${event.output_data?.keywords?.join(", ")}]`;
    case "CONCEPT_DETECTED": return `직접 ${event.output_data?.detected_concepts?.length ?? 0}개, 확장 ${event.output_data?.expanded_concepts?.length ?? 0}개`;
    case "AGENT_SELECTED":   return `${event.output_data?.routed_agents?.join(", ")} (미매핑: ${event.output_data?.unrouted_concepts?.length ?? 0}개)`;
    case "TOOL_INVOKED":     return `${event.input_data?.api_id} (${event.input_data?.agent_id})`;
    case "PLAN_CREATED":     return `step ${event.output_data?.step_count}건`;
    case "RESULTS_RERANKED": return `성공 ${event.output_data?.success_count}건`;
    case "RESPONSE_COMPLETED": return `답변 ${event.output_data?.answer_length}자`;
    default: return "";
  }
}
```

---

## 15. Intent → Concept → Agent → Tool → Evidence → Answer 연결 표시 방식

상세 패널에서 "처리 흐름" 섹션으로 표시.

```
처리 흐름 (request_id 기준 연결)

[질문]
"신용대출 금리와 필요서류 알려줘"
    │
    ▼ INTENT_ANALYZED
[의도: INQUIRY]  [키워드: 신용대출, 금리, 서류]
    │
    ▼ CONCEPT_DETECTED
[직접] CONCEPT_PERSONAL_CREDIT_LOAN
[확장] CONCEPT_INTEREST_RATE, CONCEPT_REQUIRED_DOCUMENT
    │
    ▼ AGENT_SELECTED
CONCEPT_INTEREST_RATE     →  RATE_AGENT
CONCEPT_REQUIRED_DOCUMENT →  SEARCH_AGENT
[미매핑] CONCEPT_POLICY
    │
    ▼ TOOL_INVOKED
RATE_AGENT  →  MOCK_RATE_LOOKUP    [✅ 210ms]
SEARCH_AGENT → MOCK_DOCUMENT_SEARCH [✅ 180ms]
    │
    ▼ Evidence
Evidence #12  confidence=0.82  concept=CONCEPT_INTEREST_RATE
Evidence #13  confidence=0.74  concept=CONCEPT_REQUIRED_DOCUMENT
    │
    ▼ Answer
[최종 답변 텍스트 표시]
```

**구현:** TraceEvent의 output_data를 단계별로 파싱해 연결. answer는 LeaderDecision.answer에서 읽음.

---

## 16. Missing Evidence 계산 방식

```python
def _compute_missing_evidence_concepts(
    all_concepts: list[str],
    evidences: list[EvidenceReference],
) -> list[str]:
    evidence_concepts = {ev.concept_id for ev in evidences if ev.concept_id}
    return [c for c in all_concepts if c not in evidence_concepts]
```

- `all_concepts`는 `LeaderDecision.detected_concepts` (온톨로지 확장 후 전체)
- Evidence가 없는 concept만 missing으로 표시

---

## 17. Grounding Score 계산 방식 (추정값)

현재 구조에서 answer와 evidence의 실제 연결을 추적하는 로직이 없으므로, 휴리스틱 기반 추정값으로 계산.

```python
def _compute_grounding_score(
    evidence_count: int,
    avg_evidence_confidence: float | None,
    answer_length: int,
    missing_concepts_count: int,
) -> float | None:
    if evidence_count == 0 or avg_evidence_confidence is None:
        return 0.0
    # 기본: evidence confidence 기반
    base = avg_evidence_confidence
    # missing concept 패널티 (-0.1 per missing, 최대 -0.3)
    penalty = min(missing_concepts_count * 0.1, 0.3)
    # answer가 매우 짧으면 (100자 미만) 추가 패널티
    length_penalty = 0.1 if answer_length < 100 else 0.0
    return max(0.0, round(base - penalty - length_penalty, 4))
```

> 이 값은 LLM이 실제로 evidence를 활용했는지 검증하지 않음. 구조적 추정값임을 UI에 명시.

---

## 18. 빈 데이터 Fallback 표시 방식

| 케이스 | 현재 | 개선 후 |
|---|---|---|
| Trace Events 없음 | 빈 그리드 | "Trace 데이터 없음 — 마이그레이션/Seed 상태 확인" 메시지 |
| Evidence 없음 | 빈 그리드 | "Evidence 없음 — Tool 호출 실패 또는 Mock API 미구동 가능성" |
| answer null | "아직 수기 리뷰 없음" | "(answer 저장 안 됨 — 백엔드 개선 후 표시)" |
| request_id 조회 실패 | 에러 Alert | 에러 원인 추정 메시지 포함 |
| BLOCKED status | 표시 안 됨 | 회색 Chip + "시스템 오류 — 백엔드 로그 확인" |

---

## 19. 기존 데이터 호환성

- 모든 새 DB 컬럼: nullable → 기존 레코드 영향 없음
- 모든 새 API 응답 필드: Optional → 기존 프론트 타입 확장만 필요
- `overall_result` 로직 변경: BLOCKED 추가, evidence_count=0 → FAIL 추가 → **기존 PASS 레코드 중 일부가 FAIL로 변경될 수 있음**
  - 허용 범위: evidence=0이면서 PASS였던 케이스는 실제로 PASS가 아님
- `confidence_score` 의미 변경 없음 (Tool 성공률 그대로)

---

## 20. 권한/인증 영향

- 기존: `require_admin` 의존성 → ADMIN 권한만 접근 가능
- 변경 없음 (ADMIN 유지)
- `answer` 필드 추가 시 내용이 민감할 수 있으므로 ADMIN 유지 적절

---

## 21. 테스트 전략

| 테스트 | 방법 | 완료 조건 |
|---|---|---|
| review_reason 정확성 | `test_chat.py` 연계, 각 케이스별 시나리오 | 7가지 케이스 모두 올바른 reason 반환 |
| score_breakdown 계산 | 단위 테스트 (helper 함수 분리) | 예상값과 일치 |
| BLOCKED 탐지 | 빈 DB 상태에서 요청 | status=BLOCKED 반환 |
| Trace Timeline 표시 | Swagger → /api/v1/ai/chat → 리더 평가 화면 | 11개 이벤트 순서 정상 |
| Evidence Detail 열람 | 실제 요청 후 content 펼침 | API 응답 JSON 표시 |
| answer 표시 | LeaderDecision.answer 저장 후 | 답변 텍스트 화면에 표시 |

---

## 22. 리스크 및 대응 방안

| 리스크 | 가능성 | 대응 |
|---|---|---|
| `leader_decision` answer 컬럼 추가 후 마이그레이션 실패 | 낮음 | nullable이므로 기존 데이터 영향 없음 |
| `overall_result` 로직 변경으로 기존 PASS → FAIL 변경 | 중간 | 변경 전 기존 데이터 재집계 테스트 |
| Trace Timeline 이벤트 순서 불일치 | 낮음 | `created_at` + `id` 기준 정렬 |
| score_breakdown final_score 가중치 부정확 | 중간 | 초기 단계에서 "(추정)" 명시, QA 검증 후 조정 |
| TraceEvent tool_id 수정으로 기존 쿼리 영향 | 낮음 | tool_id가 null이었으므로 기존 필터 없음 |

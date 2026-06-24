# 리더 평가 화면 — 현재 구조 분석 (CURRENT_ANALYSIS)

> 이 문서는 코드 분석 기반 확인 사실과 추정·한계 사항을 분리하여 기록한다.  
> 구현 전 반드시 이 문서를 읽고 개선 대상을 확인하라.

---

## 1. Leader Agent 처리 흐름 (확인)

`backend/app/agents/leader.py` 기준.

| 단계 | 코드 위치 | TraceEvent |
|---|---|---|
| Short Memory 로드 | `load_history()` | `MEMORY_LOADED` |
| Long-term Memory 로드 | `load_long_term_history()` | `LTM_LOADED` |
| 의도 분석 | `_analyze_intent()` | `INTENT_ANALYZED` |
| Concept 탐지 + 확장 | `_expand_via_relations()` | `CONCEPT_DETECTED` |
| Sub-Agent 라우팅 | `route_by_concepts()` | `AGENT_SELECTED` |
| Sub-Agent 실행 + Tool 호출 | `_AGENT_REGISTRY` → Sub-Agent `.run()` | `TOOL_INVOKED` × N |
| ExecutionPlan 생성 | `ExecutionPlan(...)` | `PLAN_CREATED` |
| Re-ranking | `_rerank()` | `RESULTS_RERANKED` |
| LLM 최종 요약 | `_summarize()` | (없음) |
| Evidence 간 연결 | `link_related_evidence()` | (없음) |
| LeaderDecision 기록 | `db.add(LeaderDecision(...))` | (없음) |
| Short Memory 저장 | `save_turn()` | (없음) |
| Long-term Memory 저장 | `save_long_term_memory()` | (없음) |

**주요 확인 사항:**
- LLM 최종 요약 단계에 TraceEvent 없음 → answer 생성 시간·실패 여부 추적 불가
- `link_related_evidence()` / `LeaderDecision` 저장 실패를 `except: pass`로 흡수 → 실패 여부 화면에서 식별 불가
- `answer` 필드는 `ChatResponse`에는 있지만 `LeaderEvaluationDetailResponse`에는 **없음** (항상 `null`)

---

## 2. LeaderDecision 구조 (확인)

`backend/app/models/trace_model.py:35-67`

| 필드 | 타입 | 내용 |
|---|---|---|
| `request_id` | String(100) | 요청 고유 ID |
| `detected_intent` | String(50) | 탐지된 의도 |
| `detected_concepts` | JSON | concept_id 목록 (온톨로지 확장 후 전체) |
| `selected_agents` | JSON | 배정된 agent_id 목록 |
| `reasoning` | JSON | `intent_data` 전체 (`intent`, `keywords`, `urgency`) |
| `confidence_score` | Float | 성공 API 수 / 전체 API 수 |
| `total_steps` | Integer | ExecutionStep 수 |
| `memory_turns` | Integer | 활용된 이전 대화 턴 수 |

**누락 필드:**
- `detected_concepts`가 직접 탐지 + 온톨로지 확장 후 전체 목록 (직접 탐지 vs 확장 구분 없음)
- `keywords`는 `reasoning` JSON 안에 있지만 별도 컬럼 없음 → 검색·필터 불가
- `ltm_turns` 필드 없음 (LTM 몇 턴이 활용됐는지 기록 안 됨)
- `answer` 필드 없음 → 최종 답변 텍스트와 LeaderDecision이 연결되지 않음
- concept별 → agent 매핑 이유 없음 (어떤 concept 때문에 어떤 agent가 선택됐는지 역추적 불가)

---

## 3. TraceEvent 구조 (확인)

`backend/app/models/trace_model.py:70-89`

| 필드 | 내용 |
|---|---|
| `request_id` | 요청 ID |
| `event_type` | 단계명 (REQUEST_RECEIVED, TOOL_INVOKED 등) |
| `agent_id` | 해당 단계 Agent ID (nullable) |
| `tool_id` | 해당 단계 Tool ID (nullable) |
| `input_data` | 단계 입력 JSON |
| `output_data` | 단계 출력 JSON |
| `status` | "success" / "error" (default "success") |
| `duration_ms` | 처리 시간 (ms) |

**확인된 문제:**
- `TOOL_INVOKED` 이벤트에서 `tool_id` 필드는 **항상 NULL** — `leader.py:274`에서 `tool_id` 인자 없이 `record_event()`를 호출함
- `input_data`의 `api_id`에서 tool 정보를 읽을 수 있지만 컬럼 레벨에서는 비어 있음
- `CONCEPT_DETECTED`의 `output_data`에 `detected_concepts`/`expanded_concepts`/`total_concepts` 모두 있음 → 상세 패널에서 활용 가능
- `AGENT_SELECTED`의 `output_data`에 `routed_agents`/`unrouted_concepts` 있음 → 미매핑 concept 추적 가능
- LTM 로드 이벤트(`LTM_LOADED`)의 `output_data`에 `ltm_turns_loaded`만 있고 실제 LTM 내용은 없음

---

## 4. EvidenceReference 구조 (확인)

`backend/app/models/trace_model.py:92-131`

| 필드 | 내용 |
|---|---|
| `request_id` | 요청 ID |
| `concept_id` | 관련 concept (nullable) |
| `source_id` | api_id (예: MOCK_RATE_LOOKUP) |
| `content` | API 응답 JSON 전체 |
| `confidence_score` | 최종 종합 신뢰도 (0.5×quality + 0.4×intent + 0.1×latency) |
| `data_quality_score` | 데이터 완성도 |
| `intent_relevance_score` | 의도 관련도 |
| `response_latency_ms` | API 응답 시간 |
| `item_count` | 반환 레코드 수 |
| `quality_flags` | 세부 품질 체크 결과 |
| `related_evidence_ids` | 연결된 Evidence ID 목록 (사후 link_related_evidence() 처리) |

**누락 필드:**
- `agent_id` 없음 → 어떤 Agent가 생성한 Evidence인지 직접 조회 불가
- `is_used_in_answer` 없음 → 최종 답변에 실제 반영됐는지 추적 불가
- `source_type` 필드는 있지만 저장 시 채워지지 않음 (nullable, 항상 NULL)

---

## 5. request_id 연결 구조 (확인)

```
request_id
  ├─ LeaderDecision (1:1)      — leader.py 에서 생성
  ├─ TraceEvent (1:N)          — 단계마다 기록, 평균 9~11건
  └─ EvidenceReference (1:N)   — 성공한 Tool 호출마다 1건
```

**확인된 연결 가능 여부:**

| 조회 | 가능 여부 | 비고 |
|---|---|---|
| request_id → LeaderDecision | 가능 | `leader_evaluation.py:149` |
| request_id → TraceEvent 목록 | 가능 | `leader_evaluation.py:212` |
| request_id → Evidence 목록 | 가능 | `leader_evaluation.py:217` |
| Evidence → concept_id | 가능 | `EvidenceReference.concept_id` |
| Evidence → agent_id | **불가** | 해당 컬럼 없음 |
| Evidence → 최종 답변 연결 | **불가** | answer 필드 LeaderDecision에 없음 |
| TraceEvent tool_id 조회 | **불가** | tool_id 항상 NULL |

---

## 6. 리더 평가 목록 API 구조 (확인)

`GET /api/v1/admin/leader-evaluations`  
`backend/app/api/routes/leader_evaluation.py:127-202`

**현재 동작:**
1. `TraceEvent` 전체를 `request_id` 없이 조회 (최대 `limit`건)
2. Python 메모리에서 `request_id`로 그룹화
3. 각 그룹마다 `LeaderDecision`, `EvidenceReference` 별도 조회
4. `_infer_overall_result()`로 status 계산
5. `request_id` 역순 정렬 후 반환

**성능 문제:**
- `N+1 쿼리` 구조 — 요청 수가 많아질수록 DB 부하 급증
- `TraceEvent` 전량 로드 후 Python에서 그룹화 → 대용량 시 메모리 문제
- `overall_result` 필터링은 Python 레벨에서 수행 → `limit` 전 필터가 없음

**데이터 문제:**
- `user_question`은 `REQUEST_RECEIVED` 이벤트의 `input_data.message`에서 추출 — `REQUEST_RECEIVED` 이벤트가 없으면 `null`
- `review_reason` 없음 — NEEDS_REVIEW 원인을 한 줄로 표시하는 필드 자체가 없음

---

## 7. 리더 평가 상세 API 구조 (확인)

`GET /api/v1/admin/leader-evaluations/{request_id}`  
`backend/app/api/routes/leader_evaluation.py:205-256`

**반환 구조:**

```json
{
  "request_id": "...",
  "user_question": "...",
  "answer": null,                    // 항상 null — ChatResponse에서 저장 안 함
  "leader_decision": {
    "detected_intent": "INQUIRY",
    "expected_intent": null,         // 항상 null — 수동 입력 없음
    "intent_match_yn": null,         // 항상 null
    "detected_concepts": [...],      // 온톨로지 확장 후 전체 (직접/확장 구분 없음)
    "missing_concepts": [],          // 항상 빈 배열 — 비교 로직 없음
    "extra_concepts": [],            // 항상 빈 배열
    "selected_agents": [...],
    "missing_agents": [],            // 항상 빈 배열
    "extra_agents": []               // 항상 빈 배열
  },
  "evidence_summary": { ... },
  "review": {
    "hallucination_yn": null,        // 항상 null — 탐지 로직 없음
    "review_comment": null,          // 항상 null — 수동 입력 없음
    "reviewer": null,                // 항상 null
    "overall_result": "PASS/NEEDS_REVIEW/FAIL"
  },
  "trace_events": [...],
  "evidences": [...]
}
```

---

## 8. confidence_score 계산 방식 (확인)

### LeaderDecision.confidence_score

`leader.py:344-345`

```python
success_count = sum(1 for r in raw_results if r.status == "success")
confidence = success_count / len(raw_results) if raw_results else 0.0
```

→ **Tool API 성공률만 반영.** intent 정확도, concept 품질, evidence 품질은 반영 안 됨.  
→ API 1건 성공 / 1건 전체 = 1.0, 1건 성공 / 2건 전체 = 0.5.

### EvidenceReference.confidence_score

`evidence_scorer.py:201-204`

```python
confidence = 0.5 × data_quality + 0.4 × intent_relevance + 0.1 × latency_bonus
```

- `data_quality_score`: 필수 필드 존재 여부(0.6) + 항목 수 보너스(최대 0.4) − null 필드 패널티(0.2)
- `intent_relevance_score`: `_INTENT_RELEVANCE_TABLE`에서 intent × api_id 점수 조회
- `latency_bonus`: 2초 이내=1.0 / 2~5초=0.8 / 5초 초과=0.5

---

## 9. status 계산 방식 (확인)

`leader_evaluation.py:33-44` `_infer_overall_result()`

```python
if failed_step_count > 0 or (leader_confidence is not None and leader_confidence < 0.5):
    return "FAIL"
if avg_evidence_confidence is not None and avg_evidence_confidence < 0.75:
    return "NEEDS_REVIEW"
return "PASS"
```

**현재 PASS/NEEDS_REVIEW/FAIL 기준:**

| Status | 조건 |
|---|---|
| FAIL | `failed_step_count > 0` OR `leader_confidence < 0.5` |
| NEEDS_REVIEW | `avg_evidence_confidence < 0.75` |
| PASS | 나머지 |
| BLOCKED | **없음** — 시스템 오류 구분 불가 |

**한계:**
- intent 판단 적합도 미반영
- concept 탐지 품질 미반영
- evidence 0건일 때 PASS 가능 (`avg_evidence_confidence`가 None → NEEDS_REVIEW 건너뜀)
- BLOCKED 상태 없음 → DB/API/LLM 장애와 일반 실패 구분 불가
- review_reason 없음 → 왜 NEEDS_REVIEW인지 알 수 없음

---

## 10. 프론트 리더 평가 화면 구조 (확인)

`frontend/src/app/admin/leader-evaluations/page.tsx`

**레이아웃:**
1. 상단: Request ID 검색 + 조회 버튼
2. 중단: `BaseDataGrid` (목록) + 요약 카드 (선택한 row)
3. 하단 좌: `BaseDataGrid` (Trace Events)
3. 하단 우: `BaseDataGrid` (Evidence)

**목록 컬럼:**

| 컬럼 | 필드 | 문제 |
|---|---|---|
| Request ID | `request_id` | 너무 길게 표시됨 |
| 질문 | `user_question` | 질문이 길면 잘림, tooltip 없음 |
| Intent | `detected_intent` | 색상 구분 없음 |
| Agents | `selected_agents_text` | `.join(", ")` 단순 문자열 — chip 아님 |
| Leader | `leader_confidence_score` | 원시 숫자, 레벨 시각화 없음 |
| Evidence | `avg_evidence_confidence` | 원시 숫자, 레벨 시각화 없음 |
| Result | `overall_result` | 색상 구분 없음, review_reason 없음 |

**요약 카드 (우측 패널):**
- request_id, 질문, Intent, confidence 2개, overall_result, answer review 표시
- `answer` 필드 항상 null → "아직 수기 리뷰 없음" 항상 표시
- Concept 목록, Agent 목록 없음

**리더 판단 패널:**
- Expected Intent/Concepts/Agents 비교 — 항상 null/빈 배열 → 의미 없음
- `detected_concepts`는 `renderTagList`으로 Chip 표시 (현재 유일하게 잘 구현된 부분)
- `reasoning`(intent_data JSON) 표시 없음 — keywords, urgency 확인 불가

**Trace Events 그리드:**
- `tool_id` 컬럼 항상 null
- `input_data`/`output_data` 컬럼 없음 → 단계별 상세 데이터 확인 불가
- 타임라인 형태 아님 — 단순 테이블

**Evidence 그리드:**
- `quality_flags` 컬럼 없음 → 세부 품질 체크 확인 불가
- `content` 컬럼 없음 → 원본 API 응답 확인 불가
- `agent_id` 없음 → 어떤 Agent가 생성한지 알 수 없음

---

## 11. row 선택 시 상세 패널 데이터 로딩 (확인)

```typescript
// page.tsx:89-94
const detailQuery = useQuery({
  queryKey: ["leader-evaluation-detail", selectedRequestId],
  queryFn: () => apiGet<LeaderEvaluationDetail>(`/api/v1/admin/leader-evaluations/${selectedRequestId}`),
  enabled: !!selectedRequestId,
});
```

- row 클릭 → `setSelectedRequestId(row.request_id)` → `detailQuery` 자동 실행
- `enabled: !!selectedRequestId`로 selectedRequestId가 없으면 API 호출 안 함
- **연결 자체는 정상** — row 선택 후 상세 API가 호출됨

**잠재적 문제:**
- 동일 request_id를 클릭해도 쿼리 캐시로 인해 재조회 안 됨 (TanStack Query 기본 staleTime)
- 상세 로딩 중 로딩 인디케이터 없음 (`detailQuery.isLoading` 미사용)

---

## 12. Trace Events가 비어 보이는 원인 분석

비어 보이는 케이스별 원인:

| 케이스 | 원인 | 확인 방법 |
|---|---|---|
| DB에 데이터 없음 | 마이그레이션 미실행 / Seed 미완료 | `GET /api/v1/ai/traces/{request_id}/events` 직접 호출 |
| `request_id` 불일치 | 목록에서 선택한 request_id와 detail API 호출 ID 불일치 | 브라우저 Network 탭 확인 |
| TraceEvent 저장 실패 | DB 오류, 하지만 `except: pass`로 흡수 | Backend 로그 확인 |
| AI Gateway 이전 오류 | REQUEST_RECEIVED 이전에 예외 발생 | 최초 이벤트부터 확인 |
| `AUTH_ENABLED=True`에서 권한 부족 | require_admin 조건 미충족 | 401/403 응답 확인 |

**주목할 점:**
- `record_event()`는 예외를 흡수하지 않음 → TraceEvent 저장 실패 시 전체 요청 실패
- Leader Agent 내부 예외는 흡수됨 → TraceEvent가 중간에 끊길 수 있음

---

## 13. Evidence가 비어 보이는 원인 분석

| 케이스 | 원인 | 확인 방법 |
|---|---|---|
| Tool 호출이 모두 실패 | Mock API 미구동 / 타임아웃 | `http://localhost:18010/health` 확인 |
| evidence 저장 조건 미충족 | `status == "success" and data is not None` 조건 | leader.py:279 확인 |
| `concept_id` null | api_to_concept 매핑 실패 | leader.py:256-259 확인 |
| `link_related_evidence()` 실패 | `except: pass`로 흡수 | related_evidence_ids가 빈 채로 저장됨 |
| OpenAI 없이 fallback 동작 | Tool은 성공하지만 evidence 저장은 정상 진행 | evidence_count 응답 확인 |

---

## 14. 현재 화면 UX 한계

### 운영자 관점
- NEEDS_REVIEW/FAIL이지만 **왜**인지 한 줄 설명 없음
- 환각 여부(`hallucination_yn`) 항상 null → 실용적 정보 없음
- 질문과 최종 답변을 나란히 볼 수 없음 (`answer` 항상 null)

### 개발자 관점
- `TOOL_INVOKED` 이벤트의 `tool_id` null → 어떤 API가 호출됐는지 Trace 탭에서 직접 보이지 않음
- latency가 높은 단계를 빠르게 식별하기 어려움 (단순 테이블, 정렬/하이라이트 없음)
- Evidence의 `quality_flags` (세부 품질 체크) 표시 안 됨
- 원본 API 응답(`content`) 확인 불가

### QA 관점
- `detected_concepts`가 직접 탐지 vs 온톨로지 확장으로 구분되지 않음
- `unrouted_concepts` (매핑 없는 concept) 화면에 없음
- Intent 판단 근거(`keywords`, `urgency`) 표시 안 됨
- `AGENT_SELECTED` 이벤트의 상세(어떤 concept이 어떤 agent로 매핑됐는지) 표시 안 됨

---

## 15. 현재 구조에서 바로 개선 가능한 부분 (DB/API 변경 없이)

| 항목 | 방법 | 위치 |
|---|---|---|
| Result 컬럼에 색상 칩 추가 | GridColDef renderCell | page.tsx |
| Agent 목록을 Chip으로 표시 | selected_agents_text → 배열 처리 | page.tsx listRows |
| Tool 정보를 input_data에서 읽기 | TOOL_INVOKED의 input_data.api_id | eventColumns |
| keywords/urgency 표시 | reasoning JSON 파싱 | 상세 패널 |
| detected_concepts vs expanded_concepts 구분 | CONCEPT_DETECTED 이벤트 output_data | 상세 패널 |
| unrouted_concepts 표시 | AGENT_SELECTED 이벤트 output_data.unrouted_concepts | 상세 패널 |
| concept→agent 매핑 표시 | AGENT_SELECTED 이벤트 output_data | 상세 패널 |
| Trace 타임라인 정렬 | created_at 기준 정렬 + duration bar | Trace 그리드 |
| review_reason 계산 표시 | 프론트에서 status 기반 추론 | 요약 카드 |
| 상세 로딩 인디케이터 | detailQuery.isLoading 활용 | page.tsx |

---

## 16. DB/API 변경이 필요한 부분

| 항목 | 변경 내용 | 위치 |
|---|---|---|
| answer 연결 | LeaderDecision에 `answer` 컬럼 추가 | trace_model.py + Alembic |
| agent_id 추적 | EvidenceReference에 `agent_id` 컬럼 추가 | trace_model.py + Alembic |
| review_reason | LeaderDecision 또는 별도 computed 응답 필드 추가 | schemas/leader_evaluation.py |
| score 분해 | API 응답에 score breakdown 추가 | leader_evaluation.py 계산 로직 |
| BLOCKED 상태 | status 계산 로직에 시스템 오류 케이스 추가 | leader_evaluation.py |
| tool_id 수정 | TOOL_INVOKED record_event에 tool_id 인자 전달 | leader.py:274 |
| ltm_turns 분리 | LeaderDecision에 ltm_turns 컬럼 추가 (선택) | trace_model.py |
| 직접/확장 Concept 분리 | LeaderDecision에 `direct_concepts`/`expanded_concepts` 추가 | trace_model.py |

---

## 17. Short Memory / Long-term Memory 평가 화면 노출 가능 여부

| 항목 | 현재 | 가능 여부 |
|---|---|---|
| memory_turns (단기) | LeaderDecision.memory_turns에 저장됨 | **즉시 가능** |
| ltm_turns (장기) | LTM_LOADED 이벤트 output_data.ltm_turns_loaded에 있음 | **TraceEvent 파싱으로 가능** |
| LTM 실제 내용 | 저장 안 됨 | 불가 (long_term_memory 테이블 별도 조회 필요) |
| Short Memory 내용 | Redis에만 있음 | 불가 (Redis 직접 조회 필요) |

---

## 18. Intent → Concept → Agent → Tool → Evidence → Answer 연결 검증 가능 여부

| 연결 | 현재 가능 여부 | 근거 |
|---|---|---|
| Intent | O | LeaderDecision.detected_intent |
| Intent → Keywords | O | LeaderDecision.reasoning.keywords |
| Intent → Concept | △ | CONCEPT_DETECTED 이벤트 파싱 (직접/확장 구분 있음) |
| Concept → Agent | △ | AGENT_SELECTED 이벤트 파싱 필요 |
| Agent → Tool | △ | TOOL_INVOKED 이벤트의 input_data.agent_id |
| Tool → Evidence | O | EvidenceReference.source_id = api_id |
| Evidence → Answer | X | answer 필드 없음, 연결 로직 없음 |

**결론:** Intent~Tool 구간은 TraceEvent 파싱으로 연결 가능하나 UI에 표시되지 않음.  
Evidence~Answer 구간은 현재 데이터 구조에서 연결 불가.

---

## 19. 기존 데이터와 호환성 이슈

- `LeaderDecision.answer` 추가 시 기존 레코드는 null → nullable 컬럼으로 추가 필수
- `EvidenceReference.agent_id` 추가 시 기존 레코드는 null → nullable 컬럼으로 추가 필수
- `overall_result` 계산 로직 변경 시 기존 화면에서 다른 결과가 나올 수 있음
- confidence_score 의미 변경 금지 (기존: Tool 성공률) — 새 score는 별도 필드로 추가

---

## 20. 운영자/개발자/QA 관점에서 부족한 정보 요약

### 운영자
- ❌ NEEDS_REVIEW 이유 한 줄 설명
- ❌ 최종 답변 텍스트 확인
- ❌ 환각 가능성 표시
- ❌ BLOCKED 상태 (시스템 오류 구분)

### 개발자
- ❌ TOOL_INVOKED에서 tool_id null
- ❌ latency 병목 시각화
- ❌ Evidence quality_flags 표시
- ❌ concept→agent 매핑 근거
- ❌ 원본 API 응답 확인
- ❌ answer 생성 단계 trace

### QA
- ❌ 직접 탐지 vs 확장 concept 구분
- ❌ unrouted_concepts (매핑 안 된 concept) 표시
- ❌ keywords/urgency 표시
- ❌ 예상 Intent/Concept/Agent 비교 (현재 항상 null)
- ❌ score 분해 (intent/concept/routing/tool/evidence 각각)

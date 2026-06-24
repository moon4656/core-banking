# Leader Recovery Notes

## 1. 깨진 직접 원인

- `backend/app/agents/leader.py`를 slimming/recovery 중간 상태로 두면서 질문 초점 필터링이 약화됐다.
- 그 결과 `"내 신용등급이 어떠해?"` 같은 질의에서 `MOCK_PERSONALIZED_RATE_LOOKUP` 결과만 보여야 하는데, `MOCK_PRODUCT_LOOKUP` / 일반 금리 결과까지 같이 섞였다.
- 같은 과정에서 trace/evidence 저장 흐름도 일부 빠져 `evidence_count=0`, trace list의 `intent=None` 같은 부수 증상이 생겼다.
- 추가로 legacy formatter / keyword fallback 구간에 깨진 문자열 리터럴이 남아 있어, 특정 수정 후 `leader.py` 자체가 import 불가 상태로 드러났다.

## 2. 임시 복구 중 축약되면 안 되는 helper 목록

- `_load_focus_keywords`
- `_load_api_concept_map`
- `clear_focus_keywords_cache`
- `_detect_concepts_via_synonyms`
- `_filter_results_by_question`
- `_keyword_intent`
- evidence / trace 저장 호출
  - `save_decision_trace_core`
  - `save_concept_detections`
  - `save_agent_selection_rows`
  - `save_tool_execution_rows`
  - `save_reranking_trace`
  - `save_final_answer_trace`
  - `save_evidence_with_score`
  - `link_related_evidence`

## 3. slimming 재개 전 유지해야 할 골든 테스트 목록

- `backend/tests/test_chat.py`
  - `test_chat_credit_grade_query_prefers_personalized_rate_output`
  - `test_chat_rate_query_does_not_return_product_section`
  - `test_chat_product_query_keeps_product_section`
  - `test_chat_credit_grade_query_routes_rate_agent`
  - `test_chat_credit_grade_query_plan_includes_personalized_rate_lookup`
  - `test_trace_list_includes_query_preview_and_pipeline_summary`
  - `test_chat_evidence_count`
- `backend/tests/test_leader_golden.py`
  - `test_leader_golden_credit_grade_query_detects_rate_concept`
  - `test_leader_golden_application_query`
  - `test_leader_golden_clarification_query`
  - 전체 golden suite

## 4. 다음 refactor에서 먼저 분리할 책임 / 나중에 분리할 책임

먼저 분리할 책임:
- trace/evidence 저장 orchestration
- clarification pending-state merge
- question-focused filtering
- decision trace / leader decision persistence

나중에 분리할 책임:
- legacy formatter fallback
- long-term summary generation fallback
- decision_v2 조립 세부 구조
- old helper compatibility layer

## 5. slimming 재개 조건

1. `docker compose exec backend pytest tests/test_chat.py tests/test_leader_golden.py -v` 통과
2. 신용등급 / 금리 / 상품 / 서류 / clarification 대표 질문 수동 확인
3. `evidence_count > 0`, trace list `intent` 노출 확인
4. 그 다음에만 leader slimming 재시작

## 6. 이번 복구에서 확인한 현재 기준선

- `tests/test_chat.py`: PASS
- `tests/test_leader_golden.py`: PASS
- 합본 실행: `26 passed`
- Docker 기준 검증 시점: 2026-06-24 Asia/Seoul

# Evaluation Scenario Catalog Design

## 목표

카테고리별 테스트 질의를 DB에 저장하고, 신규 Agent 추가 또는 alias/concept 변경 시 반복 가능한 회귀 평가 체계를 만드는 것이 목표다.

이 설계는 현재 프로젝트의 세 가지 평가 자산을 하나의 운영 모델로 묶는다.

- 코드 고정형 골든 시나리오: `backend/app/eval/scenarios.py`
- 샘플 시나리오 API: `backend/app/api/routes/ai_gateway.py`
- DB 기반 concept 평가: `backend/app/models/eval_model.py`, `backend/app/api/routes/concept_eval.py`

핵심 원칙은 다음과 같다.

- 테스트 자산의 기준 원천은 DB 시나리오 카탈로그로 통합한다.
- 평가는 단순 답변 품질이 아니라 concept 탐지, agent 라우팅, tool 선택, evidence 조건까지 검증한다.
- 신규 Agent 추가는 코드 반영만으로 끝나지 않고 평가 시나리오 등록까지 완료되어야 한다.

---

## 현재 구조 분석

### 이미 있는 것

1. `ConceptEvalCustomQuery`
- 카테고리, 질의, 기대 Agent 저장 가능

2. `ConceptEvalRun`, `ConceptEvalItem`
- 평가 실행 이력과 개별 결과 저장 가능

3. `app.eval.run_eval`
- `/api/v1/ai/chat` 실응답 기준 회귀 평가 가능

4. `leader_evaluation`
- 운영 Trace 기반 사후 분석 가능

### 부족한 것

1. 평가 자산이 코드와 DB에 분산되어 있다.
2. DB 평가 모델이 concept/agent 중심이라 tool, answer, evidence 기대값을 충분히 표현하지 못한다.
3. 신규 Agent 추가 시 평가 시나리오 등록을 강제하는 체크리스트가 없다.
4. 정기 실행과 배포 전 회귀 실행의 운영 규칙이 문서화되어 있지 않다.

---

## 권장 아키텍처

### 1. 시나리오 카탈로그를 DB의 기준 원천으로 승격

기존 `ConceptEvalCustomQuery`를 임시 입력 저장소로만 유지하기보다, 정식 회귀 자산을 담는 카탈로그 테이블로 확장하거나 별도 테이블을 추가한다.

권장 방향은 별도 테이블 추가다.

이유:

- `custom_query`는 운영자가 임시로 넣는 질의와 정식 회귀 자산을 구분하기 어렵다.
- 신규 Agent 체크리스트와 연결하려면 활성 여부, 우선순위, 필수 회귀 여부 같은 운영 메타데이터가 필요하다.

권장 테이블명 예시:

- `eval_scenario_catalog`

권장 필드:

- `id`
- `scenario_id`
- `category`
- `message`
- `expected_intent`
- `expected_concepts`
- `expected_agents`
- `expected_api_ids`
- `answer_must_contain`
- `answer_must_not_contain`
- `min_evidence`
- `is_active`
- `is_smoke`
- `is_regression_required`
- `priority`
- `owner`
- `tags`
- `notes`
- `created_at`
- `updated_at`

### 2. 실행 이력은 기존 eval run 구조를 재사용

현재 `ConceptEvalRun`, `ConceptEvalItem`은 실행 이력 저장 구조로 적합하다. 다만 저장 항목은 확장하는 것이 좋다.

추가 권장 필드:

- `expected_concepts`
- `expected_api_ids`
- `actual_api_ids`
- `answer_preview`
- `evidence_count`
- `intent`
- `scenario_id`
- `status`

이렇게 하면 “질의 카탈로그”와 “실행 결과 이력”이 분리되고, 반복 실행 및 비교가 쉬워진다.

### 3. 평가 기준은 라우팅 중심으로 유지

이 프로젝트는 생성형 답변 시스템이 아니라 라우팅 시스템이다. 따라서 평가 우선순위는 아래와 같이 두는 것이 맞다.

1. intent
2. direct concept
3. expanded concept
4. selected agents
5. selected api ids
6. answer include/exclude
7. evidence count

즉 “답변 문장”보다 “올바른 concept와 agent로 갔는가”가 우선이다.

---

## API 확장 방향

현재 `concept_eval` 라우터를 중심으로 확장하는 것이 자연스럽다.

### 유지할 API

- `GET /api/v1/admin/concept-eval/custom-queries`
- `POST /api/v1/admin/concept-eval/custom-queries`
- `PUT /api/v1/admin/concept-eval/custom-queries/{query_id}`
- `DELETE /api/v1/admin/concept-eval/custom-queries/{query_id}`
- `POST /api/v1/admin/concept-eval/runs`
- `GET /api/v1/admin/concept-eval/runs`
- `GET /api/v1/admin/concept-eval/runs/{run_id}`

### 추가할 API

- `GET /api/v1/admin/concept-eval/scenarios`
- `POST /api/v1/admin/concept-eval/scenarios`
- `PUT /api/v1/admin/concept-eval/scenarios/{scenario_id}`
- `DELETE /api/v1/admin/concept-eval/scenarios/{scenario_id}`
- `POST /api/v1/admin/concept-eval/scenarios/batch-run`

### batch-run 동작 원칙

- active scenario만 기본 실행
- `category`, `tags`, `is_smoke`, `is_regression_required` 필터 지원
- 실행 시 `/api/v1/ai/chat` 또는 내부 Leader 호출 중 하나를 기준으로 고정
- 실행 결과는 run/item 이력으로 저장

---

## 운영 플로우

### 신규 Agent 추가 시

1. Agent 구현
2. `_AGENT_REGISTRY` 등록
3. `agents_seed.py`, `mappings_seed.py`, 필요 시 `tools_seed.py` 반영
4. 해당 Agent 도메인의 시나리오 카탈로그 등록
5. 도메인 smoke 시나리오 실행
6. 전체 active 회귀 시나리오 실행
7. 실패한 alias/concept/tool 라우팅 수정
8. 문서와 테스트 갱신

### alias 또는 concept 변경 시

1. 변경된 concept에 연결된 시나리오만 부분 실행
2. 이후 전체 회귀 실행
3. 최근 production trace에서 실패/혼동 질의를 시나리오로 승격

### 정기 운영 시

- 일일 또는 주간 단위로 active regression 세트 실행
- 최근 실패율이 높은 category를 우선 재평가
- production trace 기반 신규 질의 후보를 DB에 축적

---

## 시나리오 분류 기준

권장 카테고리는 현재 도메인 기준으로 나누는 것이 가장 운영 친화적이다.

- `loan`
- `rate`
- `policy`
- `search`
- `forex`
- `notification`
- `cross_domain`
- `guardrail`

추가 태그 예시:

- `alias`
- `smoke`
- `regression`
- `high_risk`
- `new_agent`
- `production_promoted`

이렇게 두면 “외환 alias만 재검증”, “신규 agent smoke만 실행”, “운영 유입 기반 질의만 재평가” 같은 실행이 쉬워진다.

---

## 현재 코드 기준 최소 구현 순서

1. DB 스키마 설계 추가
- `eval_scenario_catalog` 신규 테이블

2. API 스키마 확장
- scenario CRUD
- category/tag 기반 조회
- batch-run 진입점

3. 평가 로직 확장
- concept/agent 외에 api, answer, evidence 검증 추가

4. 정적 시나리오 정리
- `app/eval/scenarios.py` 는 초기 seed 소스나 백업 fixture 역할로 축소
- 운영 기준은 DB로 이동

5. 신규 Agent 체크리스트 반영
- 문서와 구현 절차에서 scenario 등록을 필수 단계로 격상

---

## 비목표

이번 설계의 비목표는 다음과 같다.

- 운영 스케줄러를 즉시 도입하는 것
- LLM judge 기반 자유 서술 평가를 도입하는 것
- 모든 production trace를 자동으로 시나리오화하는 것

우선은 DB 카탈로그 기반의 결정적 회귀 체계를 만드는 것이 먼저다.

---

## 권장 결론

현재 프로젝트는 이미 DB 기반 평가 구조를 일부 갖고 있으므로, 완전히 새 시스템을 만드는 것보다 기존 `concept_eval`을 중심으로 “시나리오 카탈로그 + 실행 이력 확장”으로 정리하는 것이 가장 적은 변경으로 가장 큰 효과를 낸다.

신규 Agent 추가의 완료 조건은 앞으로 아래처럼 보는 것이 맞다.

- Agent 코드가 존재한다.
- seed/mapping/tool 연결이 반영되었다.
- 해당 Agent의 카테고리별 평가 시나리오가 DB에 등록되었다.
- smoke와 전체 회귀 평가를 통과했다.

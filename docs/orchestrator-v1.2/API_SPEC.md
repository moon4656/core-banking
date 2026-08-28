# API_SPEC — K Region AI Agent Orchestrator (ERD v1.2 Baseline)

## 1. API 원칙

- 외부/관리 API Prefix 등 기존 규약은 유지할 수 있다.
- 본 문서는 현재 프로젝트의 실행 순서와 책임 경계를 정의한다.
- 요청 접수 시 execution을 선생성하지 않는다.
- Worker용 Claim/Heartbeat/Recovery API는 만들지 않는다.
- Policy/Rule/Governance API는 만들지 않는다.

## 2. 고객 요청 API

논리 Endpoint:

```http
POST /api/v1/agent/execute
```

요청 스키마의 정확한 필드는 기존 Contract/ERD v1.2 정의를 따른다.

처리 순서:

```text
1. 인증/인가
2. 입력 검증
3. Service/Environment 확인
4. 승인된 Master Agent Registry Version 확인
5. runtime_artifact_version 확인
6. master_agent_endpoint 확인
7. Master Agent 호출
8. Master Agent가 P Region Leader 실행
9. 결과 수신
10. execution 저장
11. Structured Trace가 있으면 execution_step 저장
12. 결과 반환
```

### 응답 원칙

현재 구조는 `202 + execution_id`를 먼저 반환하는 Queue 기반 모델을 기본으로 하지 않는다.

결과 수신 후 저장된 execution의 식별자를 응답에 포함할 수 있으나, 실제 응답 Schema는 기존 API Contract 승인 후 확정한다.

## 3. Execution 조회 API

논리 Endpoint 예:

```http
GET /api/v1/executions/{execution_id}
```

조회 대상은 이미 저장된 execution이다.

- Queue 진행상태 Polling API로 사용하지 않는다.
- execution 상태값을 API 문서에서 새로 추가하지 않는다.
- Structured Trace가 없는 execution은 Step 목록이 비어 있을 수 있다.

## 4. Registry API

필요 기능:

```text
Registry Component 조회/관리
Registry Version 조회/관리
Runtime Artifact Version 조회/관리
```

Source Group:

```text
UI
API
MASTER_AGENT
```

요청/응답 필드는 ERD v1.2 물리 모델과 일치해야 한다.

## 5. Master Agent Endpoint API

관리 기능:

```text
Master Agent Endpoint 조회
Master Agent Endpoint 등록/변경
활성/승인 처리(ERD v1.2에 정의된 범위)
```

정확한 REST Path와 Payload는 `master_agent_endpoint` 물리 Schema 확인 후 확정한다.

금지:

- 사용자 입력 URL을 검증 없이 운영 Endpoint로 즉시 반영
- runtime_artifact_version에 임의 Endpoint 필드 추가

## 6. Master Agent 내부 호출 Contract

API → Master Agent 논리 Contract:

```text
Request Context
Approved Master Agent Version
Target/Allowed P Region Leader 정보
Trace/Request Correlation 정보
```

Master Agent → API 결과:

```text
Execution Result
P Region Leader 식별정보
Optional Structured Trace
Runtime/Version evidence if contract provides it
```

필드명은 별도 Contract 확정 전 임의로 DB 컬럼화하지 않는다.

## 7. P Region Contract

Master Agent → P Region Leader에 최소 필요한 동작:

```text
Execute
Optional Status Query
Health
```

Status Query는 Timeout 후 실행 여부 불확실성을 줄이는 데 유용하지만, P Region 실제 Contract가 지원하는 경우에만 사용한다.

## 8. 오류 처리

오류 코드는 기존 공통 Error Contract를 사용한다.

본 문서에서 새로운 DB 상태값을 오류코드와 연동해 만들지 않는다.

주요 논리 오류 범주:

- Master Agent Version 미승인
- Runtime Artifact 불일치
- Master Agent Endpoint 없음/비정상
- P Region Timeout
- P Region 연결 실패
- P Region 결과 Schema 오류
- execution DB 저장 실패

정확한 오류 코드 문자열은 기존 승인 목록과 대조 후 확정한다.

## 9. Retry API 정책

- 고객 요청을 Queue에 저장한 뒤 서버가 장기 Retry하는 API 모델은 사용하지 않는다.
- 멱등성이 확인된 조회 호출에 한해 내부 제한 Retry 가능
- 실행 여부 불명확한 요청은 Status Query 우선
- Retry용 신규 execution 상태 또는 Scheduler API를 만들지 않는다.

## 10. 제거 API

현재 기준에서 만들지 않는다.

- Worker Claim API
- Heartbeat API
- Lease Recovery API
- Retry Scheduler API
- Policy/Rule CRUD API
- Governance Check API

# PRD — K Region AI Agent Orchestrator (ERD v1.2 Baseline)

## 1. 문서 기준

이 문서는 현재 프로젝트의 최신 확정 기준인 **ERD v1.2**를 따른다. 구버전 문서와 충돌할 경우 본 기준을 우선한다.

공통 확정 사항:

- Source Group은 `UI`, `API`, `MASTER_AGENT` 3개만 사용한다.
- 고객 요청 시작 시 `execution`을 생성하지 않는다.
- Master Agent가 P Region Leader를 실행하고 결과를 받은 후 `execution`을 저장한다.
- `execution_step`은 P Region이 구조화된 Trace를 제공한 경우에만 저장한다.
- Worker / Queue / Claim / Lease / Heartbeat 구조를 사용하지 않는다.
- Policy / Rule / Governance 구조를 사용하지 않는다.
- Master Agent는 `registry_component → registry_version → runtime_artifact_version`으로 관리한다.
- Master Agent의 WAS 주소는 `master_agent_endpoint`에서 관리한다.
- ERD v1.2에 없는 테이블·컬럼·관계·상태값은 승인 없이 추가하거나 변경하지 않는다.

## 2. 제품 정의

K Region AI Agent Orchestrator는 승인된 UI/API/Master Agent 구성과 버전을 관리하고, 고객 요청을 적절한 Master Agent로 전달하며, Master Agent가 P Region Leader를 실행한 결과를 기준으로 실행 이력을 저장·조회할 수 있게 하는 관리·실행 통제 플랫폼이다.

핵심 목적은 K Region이 P Region 내부 Sub-Agent/Tool 실행구조를 직접 관리하는 것이 아니라, **승인된 Master Agent와 P Region Leader 사이의 실행 경계, 버전, Endpoint, 결과 및 Trace를 통제 가능하게 유지하는 것**이다.

## 3. 핵심 목표

1. UI/API/MASTER_AGENT를 하나의 Registry 체계에서 식별하고 버전 관리한다.
2. Master Agent Runtime을 `registry_component → registry_version → runtime_artifact_version` 관계로 관리한다.
3. Master Agent의 실제 호출 대상 WAS 주소는 `master_agent_endpoint`에서 관리한다.
4. 고객 요청 처리 과정에서 사전 `execution` 생성, Queue 적재, Worker 선점 상태를 만들지 않는다.
5. Master Agent가 P Region Leader 실행 결과를 수신한 뒤 `execution`을 저장한다.
6. P Region이 Structured Trace를 제공한 경우에만 해당 Trace를 `execution_step`으로 저장한다.
7. P Region 내부 Sub-Agent/Tool Routing은 P Region Leader 책임으로 유지한다.
8. Timeout, 연결 실패, P Region 장애 등은 Runtime 통신 수준에서 제한적으로 처리하고 별도 Worker 복구 시스템을 만들지 않는다.
9. 배포·버전·Endpoint 변경은 승인된 ERD v1.2 구조 안에서만 수행한다.
10. 운영·감사·관제에서 요청 → Master Agent → P Region Leader → 결과의 연결관계를 추적 가능하게 한다.

## 4. 비목표

현재 범위에서 다음은 사용하지 않는다.

- 별도 `execution-worker`
- DB Queue 또는 외부 Queue
- Claim / Lease / Heartbeat / Recovery Scheduler
- Worker 재선점
- Policy / Rule / Governance Engine 및 관련 테이블
- K Region의 P Region Sub-Agent/Tool 직접 Registry 관리
- Master Agent의 P Region 내부 Sub-Agent 직접 선택
- P Region Structured Trace가 없는 경우 K Region이 임의로 `execution_step` 생성
- ERD v1.2에 없는 장애복구·배포·상태이력 테이블의 임의 추가

## 5. 주요 사용자

| 사용자 | 주요 목적 |
|---|---|
| 고객 채널 | Agent 요청 전송 및 결과 수신 |
| 관리 운영자 | Component/Version/Runtime Artifact/Endpoint 관리 |
| 승인자 | 승인 대상 Version 및 배포 대상 검토 |
| Agent 운영자 | Master Agent Version 및 Runtime Artifact 관리 |
| SRE/운영자 | Master Agent/P Region 통신·장애·배포 관제 |
| 감사/보안 담당자 | 실행 결과·Trace·변경 이력 검토 |

## 6. 제품 범위

### 6.1 Management

- 사용자·권한 등 ERD v1.2에 존재하는 관리 기능
- Registry Component / Registry Version 관리
- Runtime Artifact Version 관리
- Source Group 관리: UI / API / MASTER_AGENT
- Master Agent Endpoint 관리
- P Region 및 Leader 관련 승인 정보 관리(ERD v1.2 범위)
- 승인된 버전의 배포 및 운영 상태 확인
- Audit/Trace 조회(ERD v1.2 범위)

### 6.2 Runtime

기본 실행 흐름:

```text
Customer Request
  → API
  → Master Agent 선택/호출
  → Master Agent가 P Region Leader 실행
  → P Region 결과 수신
  → execution 저장
  → Structured Trace가 있으면 execution_step 저장
  → 고객에게 결과 반환
```

`execution`은 실행 중 작업 큐나 Worker 제어 레코드가 아니라 **실행 결과 이력**으로 취급한다.

## 7. Master Agent 관리 요구사항

1. Master Agent는 Source Group `MASTER_AGENT`로 구분한다.
2. Component의 논리 식별은 `registry_component`에서 관리한다.
3. Version은 `registry_version`으로 관리한다.
4. 실제 배포 가능한 Runtime Artifact 버전은 `runtime_artifact_version`으로 연결한다.
5. 실제 WAS 호출 주소는 `master_agent_endpoint`에서 관리한다.
6. Endpoint를 Runtime Artifact Version 자체의 물리 주소로 대체하지 않는다.
7. Version 또는 Endpoint의 승인·활성 조건은 ERD v1.2의 기존 상태값만 사용한다.

## 8. Execution 요구사항

1. 고객 요청 수신 직후 `execution`을 생성하지 않는다.
2. Queue 대기 상태를 `execution`으로 표현하지 않는다.
3. Master Agent가 P Region Leader 결과를 받은 후에만 `execution`을 저장한다.
4. P Region이 실패 결과를 정상 Contract로 반환한 경우 그 결과를 기준으로 저장할 수 있다.
5. 네트워크 Timeout 등으로 결과 자체를 확인하지 못한 경우 사전 생성된 `execution`을 복구하는 방식은 사용하지 않는다.
6. Execution 상태값은 ERD v1.2 승인 값만 사용하며 본 문서에서 신규 상태를 정의하지 않는다.

## 9. Execution Step 요구사항

1. `execution_step`은 필수 저장 대상이 아니다.
2. P Region Leader가 Structured Trace를 반환한 경우에만 저장한다.
3. Trace가 없으면 `execution`만 저장한다.
4. K Region이 Context, Routing, Retry 등의 내부 이벤트를 임의 Step으로 합성하지 않는다.
5. Trace Mapping 규칙은 P Region Contract로 정의하되 신규 컬럼이 필요하면 ERD 변경 승인을 먼저 받는다.

## 10. 복원력 및 장애 대응 요구사항

현재 프로젝트는 복구형 Queue 시스템을 사용하지 않는다. 필요한 복원력은 다음 범위로 제한한다.

- API/Master Agent Runtime의 다중 Replica 또는 WAS HA
- Master Agent → P Region 호출 Timeout
- 연속 장애에 대한 Circuit Breaker 또는 동등 수준 보호
- P Region Timeout 시 Blind Retry 방지
- 가능하면 P Region 호출 식별자와 상태조회 Contract 활용
- DB 저장 실패 시 P Region 실행을 무조건 재호출하지 않고 저장 재시도와 외부 실행 재시도를 구분
- 배포 실패 시 이전 정상 Runtime으로 복원 가능한 운영 절차

## 11. 보안 요구사항

- 인증·인가 방식은 기존 프로젝트 보안 기준을 적용한다.
- 고객 인증 Token을 P Region에 그대로 전달하지 않는다.
- K/P Region 통신은 승인된 보안 채널을 사용한다.
- Endpoint는 운영자가 임의 문자열로 우회 등록하지 못하도록 승인·검증 절차를 둔다.
- 로그 및 Trace에 민감정보가 노출되지 않아야 한다.

## 12. 성공 기준

| 지표 | 목표 |
|---|---:|
| 미승인 Master Agent Version 실행 | 0건 |
| 미승인 Endpoint 사용 | 0건 |
| 요청 시작 시 사전 execution 생성 | 0건 |
| Structured Trace 없는 execution_step 생성 | 0건 |
| Worker/Queue/Lease/Heartbeat 의존 구현 | 0건 |
| Policy/Rule/Governance 신규 구현 | 0건 |
| P Region Timeout 후 무조건 Blind Retry | 0건 |
| 요청-결과 Trace 연결 가능률 | 운영 요구 수준 충족 |

## 13. Open Item

다음 항목은 ERD v1.2 또는 외부 Contract의 확정본을 대조한 뒤 구현한다.

- `runtime_artifact_version` 정확한 물리 컬럼
- `master_agent_endpoint` 정확한 컬럼과 활성/이력 규칙
- P Region Leader Execute/Status/Health Contract
- P Region Structured Trace Schema
- GreenWhales 또는 실제 배포 시스템 Contract
- 운영 TPS/SLA 및 Timeout 값

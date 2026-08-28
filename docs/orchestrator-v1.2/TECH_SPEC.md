# TECH_SPEC — K Region AI Agent Orchestrator (ERD v1.2 Baseline)

## 1. 기술 기준

본 문서는 PRD의 ERD v1.2 기준을 구현 관점에서 구체화한다. 별도 Queue/Worker 기반 비동기 실행 모델은 사용하지 않는다.

기술 핵심:

- Source Group: UI / API / MASTER_AGENT
- Registry 중심 버전 관리
- Master Agent Runtime Artifact 관리
- Endpoint와 Artifact Version 분리
- 동기 또는 요청-응답형 Master Agent → P Region Leader 실행
- 결과 수신 후 execution 저장
- Structured Trace가 있을 때만 execution_step 저장
- Timeout/Circuit Breaker 중심의 경량 복원력

## 2. 기술 스택

기존 프로젝트에서 확정된 기술 스택은 유지할 수 있으나, ERD v1.2와 충돌하는 Queue/Worker 전제는 제거한다.

| 계층 | 기준 |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite + Pinia |
| Backend | Python 3.11+ + FastAPI + Pydantic |
| ORM/Migration | SQLAlchemy 2 + Alembic |
| DB | PostgreSQL 15+ |
| HTTP | Async HTTP Client + Connection Pool |
| Deployment | OCP/Kubernetes + 기존 배포 체계 |
| Observability | OpenTelemetry 계열 Trace/Metrics |
| Security | OIDC/JWT, Service Identity, mTLS 등 기존 기준 |

제외:

- PostgreSQL Queue
- `FOR UPDATE SKIP LOCKED` 실행 선점
- Kafka/Celery/Redis Queue
- execution-worker
- Lease/Heartbeat Scheduler

## 3. Source Group

Registry Component는 다음 세 Source Group으로 구분한다.

```text
UI
API
MASTER_AGENT
```

이 값 외의 Source Group을 추가하려면 ERD/코드값 변경 승인이 필요하다.

## 4. Registry Runtime 모델

### 4.1 공통 관계

```text
registry_component
  → registry_version
      → runtime_artifact_version
```

Master Agent도 이 공통 모델을 따른다.

### 4.2 Master Agent

Master Agent는 다음을 분리해서 관리한다.

- 논리 Component: `registry_component`
- 승인 Version: `registry_version`
- 배포 Artifact Version/Digest: `runtime_artifact_version`
- 실제 WAS 주소: `master_agent_endpoint`

`runtime_artifact_version`에 운영 Endpoint를 합쳐 저장하는 방식으로 변경하지 않는다.

## 5. Runtime 요청 처리

### 5.1 기본 순서

```text
1. 고객 요청 인증/검증
2. 대상 Service/환경 확인
3. 사용할 Master Agent의 승인 Version/Runtime 정보 확인
4. master_agent_endpoint를 통해 Master Agent 호출
5. Master Agent가 승인된 P Region Leader를 실행
6. P Region Leader가 결과 및 선택적으로 Structured Trace 반환
7. K Region이 execution 저장
8. Structured Trace가 존재하면 execution_step 저장
9. 결과 반환
```

### 5.2 금지 흐름

```text
요청 수신
→ execution QUEUED INSERT
→ Worker Claim
→ PROCESSING
→ Lease/Heartbeat
→ 재선점
```

위 흐름은 현재 프로젝트에서 사용하지 않는다.

## 6. Execution 저장 기술 규칙

- `execution`은 요청의 진행중 상태 제어용 Queue Row가 아니다.
- 실행 결과를 수신한 이후 저장한다.
- DB Transaction은 execution 저장과 필요한 연관 데이터 저장의 원자성을 보장해야 한다.
- execution 컬럼 및 상태값은 ERD v1.2 그대로 사용한다.
- 과거 문서의 `claimed_by`, `lease_expires_at`, `retry_count`, `next_retry_at` 등의 사용 여부를 본 문서에서 새로 결정하지 않는다. ERD v1.2 원문과 대조한다.

## 7. Execution Step 저장 기술 규칙

```text
if p_region_response.structured_trace exists:
    save execution_step mapped from trace
else:
    do not create execution_step
```

- K Region이 자체 수행 단계를 임의로 `execution_step`으로 생성하지 않는다.
- P Region Trace Schema와 ERD v1.2 컬럼 간 Mapping이 불가능하면 스키마를 임의 확장하지 않고 변경 승인을 요청한다.

## 8. Master Agent → P Region 통신

### 8.1 Timeout

연결·응답 Timeout을 반드시 설정한다. Timeout 값은 운영 Config이며 DB 상태값이 아니다.

### 8.2 Retry

- 조회성이고 멱등성이 확실한 호출만 제한적으로 Retry할 수 있다.
- 실행 여부가 불명확한 요청은 Blind Retry하지 않는다.
- P Region이 idempotency/status 조회 Contract를 제공하면 이를 우선 활용한다.

### 8.3 Circuit Breaker

P Region의 연속 장애가 K Region Thread/Connection Pool 고갈로 확산되는 것을 막기 위해 Runtime 수준의 Circuit Breaker 또는 동등한 보호 장치를 사용할 수 있다.

이 기능을 위해 신규 DB 테이블을 만들지 않는다.

## 9. DB 실패 처리

가장 주의할 경계:

```text
P Region 실행 성공
→ 결과 수신
→ DB execution 저장 실패
```

원칙:

1. DB 저장 실패와 P Region 실행 실패를 구분한다.
2. DB 저장 Retry 때문에 P Region 실행을 재호출하지 않는다.
3. Transaction Retry는 DB 오류 성격에 맞게 제한한다.
4. 추가 영속 복구 구조가 필요해지면 ERD 변경 승인 후 도입한다.

## 10. Observability

최소 추적 필드의 실제 컬럼/속성은 기존 ERD/공통 Trace Contract를 따른다.

논리 추적 흐름:

```text
Customer Request
  → API Trace
  → Master Agent Invocation
  → P Region Leader Invocation
  → P Region Result
  → execution
  → optional execution_step
```

Queue Depth, Lease Expired, Worker Claim Rate 등은 현재 구조의 핵심 Metric에서 제외한다.

주요 Metric:

- API latency/error
- Master Agent latency/error
- P Region latency/error/timeout
- Circuit open count
- execution DB save error
- Runtime Artifact/Endpoint 불일치
- 배포/Health 오류

## 11. 보안

- 고객 Token의 P Region 직접 전달 금지
- K/P Region 구간 보안 채널 사용
- Endpoint allowlist/인증서 검증 등 기존 보안 기준 유지
- Artifact Digest와 Endpoint 등록 권한 분리 권고
- Secret/Token/민감 Trace 로그 금지

## 12. 구현 금지사항

- execution-worker 추가
- Queue/Claim/Lease/Heartbeat 구현
- RETRY_WAIT용 Scheduler 구현
- Policy/Rule/Governance Package 및 DB 구조 추가
- Structured Trace 없는 execution_step 합성
- `master_agent_endpoint` 대신 임의 Endpoint 컬럼 신설
- ERD v1.2 미확정 상태값 추가

## 13. 미확정 기술 항목

- Master Agent 호출 Contract
- P Region Execute/Status Contract
- Structured Trace Schema
- runtime_artifact_version 물리 Schema
- master_agent_endpoint 물리 Schema
- 배포 시스템 Callback/Polling Contract

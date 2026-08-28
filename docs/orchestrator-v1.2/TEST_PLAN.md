# TEST_PLAN — K Region AI Agent Orchestrator (ERD v1.2 Baseline)

## 1. 목적

ERD v1.2 기준으로 Registry/Version/Runtime Artifact/Endpoint 관리와 실제 요청 실행 흐름이 일치하는지 검증한다.

특히 다음을 보장한다.

- 요청 시작 시 execution 미생성
- P Region 결과 수신 후 execution 생성
- Structured Trace가 있을 때만 execution_step 생성
- Worker/Queue/Lease/Heartbeat 미사용
- Policy/Rule/Governance 미사용
- Master Agent Version/Artifact/Endpoint 정합성
- P Region Timeout 및 DB 저장 장애 시 중복 실행 위험 최소화

## 2. 테스트 레벨

- Unit
- API Integration
- DB Transaction
- K/P Region Contract
- E2E
- Failure Injection
- Security
- Performance
- Deployment/Recovery

Queue Concurrency/Worker Claim/Lease Heartbeat 테스트는 제거한다.

## 3. 핵심 수용 테스트

### T-001 Source Group

UI/API/MASTER_AGENT 외 값 등록 시도.

기대: 기존 코드/DB 규칙에 따라 차단. 임의 신규 값 생성 없음.

### T-002 Master Agent Registry Chain

Master Agent Component 등록 후 Version과 Runtime Artifact Version을 연결한다.

기대:

```text
registry_component
→ registry_version
→ runtime_artifact_version
```

관계가 ERD v1.2와 일치한다.

### T-003 Master Agent Endpoint

승인된 Master Agent에 `master_agent_endpoint`를 통해 WAS 주소를 연결한다.

기대: Runtime Artifact 정보와 Endpoint 정보가 분리 관리된다.

### T-004 요청 시작 시 execution 미생성

1. 고객 요청 수신
2. Master Agent 호출 직전 DB 확인
3. P Region 실행 중 DB 확인

기대: 해당 요청의 execution이 아직 생성되지 않는다.

### T-005 결과 후 execution 생성

P Region Leader가 정상 결과를 반환한다.

기대: 결과 수신 후 execution 1건 생성.

### T-006 Structured Trace 있음

P Region이 정상 결과 + Structured Trace 반환.

기대:

- execution 생성
- Trace Mapping 가능한 범위의 execution_step 생성

### T-007 Structured Trace 없음

P Region이 정상 결과만 반환.

기대:

- execution 생성
- execution_step 0건

### T-008 K Region Step 합성 금지

API/Master 내부 단계가 존재하더라도 P Region Structured Trace가 없는 케이스.

기대: execution_step 생성 금지.

### T-009 P Region Timeout

Master Agent → P Region 요청 Timeout.

기대:

- Blind Retry 정책 위반 없음
- 지원되는 경우 Status Query 수행
- Queue/RETRY_WAIT/Lease 상태 생성 없음

### T-010 DB 저장 실패

P Region 결과를 정상 수신한 직후 DB 오류 주입.

기대:

- DB 오류로 P Region 요청을 무조건 재실행하지 않음
- 저장 재시도와 외부 실행 재시도 분리

### T-011 Worker 구조 부재

코드/배포/DB 접근 경로 점검.

기대:

- execution-worker 없음
- Claim SQL 없음
- Lease/Heartbeat Scheduler 없음

### T-012 Policy/Governance 구조 부재

기대:

- Policy/Rule/Governance API/Service/DB 사용 없음

## 4. Contract 테스트

### Master Agent

- Registry Version 일치
- Runtime Artifact Version 일치
- Endpoint Resolve
- Timeout
- Response Schema

### P Region

- 인증/보안 채널
- Leader 호출 성공/실패
- Timeout
- Status Query(지원 시)
- Health
- Structured Trace Schema

## 5. 보안 테스트

- 관리 API 인증/인가
- Endpoint 변경 권한
- 고객 Token P Region 비전달
- Secret/PII 로그 노출
- Endpoint allowlist 또는 동등 통제
- Container non-root/read-only 적용 여부(배포 기준에 포함된 경우)

## 6. 성능 테스트

주요 지표:

- 고객 API E2E latency
- Master Agent latency
- P Region latency
- DB execution insert latency
- Structured Trace 저장 비용
- API/DB connection pool 안정성

제거 지표:

- Queue Claim TPS
- Queue oldest age
- Worker throughput
- Lease update 부하

## 7. 장애주입

- API Pod Kill
- Master Agent Runtime Kill
- Master Agent Endpoint 연결 실패
- P Region 5xx
- P Region Timeout
- DB connection pool exhaustion
- DB insert failure after P Region success
- Observability backend down

## 8. 배포/복구 테스트

- 신규 Runtime Health 실패
- 잘못된 Endpoint 연결 차단
- 정상 Runtime/Endpoint 복원
- Artifact Version과 배포 대상 불일치 검증

구버전 Canary 5→10→25→50→100 테스트는 ERD v1.2에서 별도 승인되지 않는 한 기본 수용 테스트에서 제외한다.

## 9. 종료 기준

- v1.2 필수 요구 테스트 100% 통과
- 사전 execution 생성 0건
- Structured Trace 없는 execution_step 생성 0건
- Worker/Queue/Lease/Heartbeat 구현 0건
- Policy/Rule/Governance 구현 0건
- 미승인 Master Agent Version/Endpoint 실행 0건
- Timeout Blind Retry 위반 0건
- 주요 요청 Trace 연결 검증 완료

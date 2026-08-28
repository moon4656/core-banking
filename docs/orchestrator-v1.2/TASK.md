# TASK — Phase Gated Development Plan (ERD v1.2 Baseline)

## 1. 실행 원칙

문서 적용 순서:

```text
PRD
→ TECH_SPEC
→ ARCHITECTURE
→ DATA_MODEL
→ API_SPEC
→ UI_DESIGN
→ DEPLOYMENT
→ TEST_PLAN
→ TASK
```

공통 금지:

- ERD v1.2 승인 없는 테이블/컬럼/관계/상태 추가
- Worker/Queue/Lease/Heartbeat 도입
- Policy/Rule/Governance 도입
- 요청 시작 시 execution 사전 생성
- P Region Trace 없이 execution_step 생성

## 2. Phase 0 — 기준선 고정

### 목표

ERD v1.2 원문과 현 문서 세트의 물리 정합성을 확보한다.

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P0-001 | ERD v1.2 원문 대조 | 테이블/컬럼/관계/상태 Diff 완료 |
| P0-002 | Source Group 확인 | UI/API/MASTER_AGENT 3개 확인 |
| P0-003 | runtime_artifact_version 확인 | 정확한 컬럼/FK 확정 |
| P0-004 | master_agent_endpoint 확인 | 정확한 컬럼/FK/상태 확정 |
| P0-005 | execution 확인 | 결과 후 저장 가능한 컬럼/상태 확인 |
| P0-006 | execution_step 확인 | Structured Trace Mapping 가능성 확인 |
| P0-007 | P Region Contract 확인 | Execute/Status/Health/Trace 확정 |
| P0-008 | 배포 Contract 확인 | 실제 배포/Health/Rollback 방식 확정 |

**Gate:** ERD v1.2와 문서 차이 0건 또는 승인된 변경 목록 존재.

## 3. Phase 1 — Registry/공통 기반

### 범위

- 공통 Backend/Frontend 기반
- DB Migration Baseline
- Registry Component/Version
- Source Group
- Runtime Artifact Version
- Auth/Trace/Error 공통 규약

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P1-001 | DB Baseline | ERD v1.2와 일치 |
| P1-002 | Registry Component | Source Group 3종 적용 |
| P1-003 | Registry Version | v1.2 상태/관계 적용 |
| P1-004 | Runtime Artifact Version | v1.2 Schema 적용 |
| P1-005 | 공통 인증/권한 | 관리 API 권한 검증 |
| P1-006 | Request/Trace | K→Master→P 상관관계 추적 가능 |
| P1-007 | Error Contract | 승인된 오류 규약 적용 |

### 금지

- Master Agent 실제 호출
- execution 사전 생성 구현
- Worker Skeleton 생성

## 4. Phase 2 — Master Agent 관리

### 범위

- MASTER_AGENT Source Group
- Master Agent Version 관리
- Runtime Artifact 연결
- `master_agent_endpoint` 관리
- Endpoint Health/검증

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P2-001 | MASTER_AGENT Component 관리 | Registry 등록/조회 |
| P2-002 | Master Agent Version 관리 | 승인 규칙 적용 |
| P2-003 | Runtime Artifact 연결 | Version-Artifact 정합성 |
| P2-004 | Endpoint 관리 | master_agent_endpoint CRUD/권한 |
| P2-005 | Endpoint Validation | Health/접근 검증 |
| P2-006 | 운영 대상 Resolve | API가 승인 Endpoint 해석 가능 |

### 금지

- Endpoint 신규 컬럼을 Artifact에 추가
- 사용자 입력 Endpoint 무검증 운영 반영

## 5. Phase 3 — P Region Contract/연계

### 범위

- Master Agent → P Region Leader 호출
- Timeout
- Circuit Breaker
- Status Query(지원 시)
- Structured Trace 수신

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P3-001 | Execute Contract | 요청/응답 Schema 검증 |
| P3-002 | 인증/보안 | K/P 보안 연결 성공 |
| P3-003 | Timeout | 상한시간 적용 |
| P3-004 | Circuit Breaker | 연속 장애 확산 차단 |
| P3-005 | Status Query | Contract 지원 시 실행여부 확인 |
| P3-006 | Trace Contract | Structured Trace Schema 검증 |
| P3-007 | Blind Retry Guard | 불명확 요청 자동 재실행 0건 |

### 금지

- Worker Retry Scheduler
- P Region Sub-Agent 직접 Routing

## 6. Phase 4 — 고객 실행 흐름

### 범위

- 고객 요청 API
- Master Agent 호출
- P Region 결과 수신
- execution 저장
- optional execution_step 저장

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P4-001 | Execute API | 요청→결과 흐름 동작 |
| P4-002 | 사전 execution 금지 | P Region 결과 전 execution 0건 |
| P4-003 | Result Persist | 결과 후 execution 저장 |
| P4-004 | Trace Persist | Structured Trace 있을 때만 Step 저장 |
| P4-005 | No-Trace Case | execution_step 0건 정상 처리 |
| P4-006 | DB Failure Handling | P 실행 재호출과 저장 Retry 분리 |
| P4-007 | Execution 조회 | 저장 완료 이력 조회 |

### 금지

- 202 + QUEUED를 기본 실행모델로 구현
- Claim/Lease/Heartbeat
- RETRY_WAIT Scheduler

## 7. Phase 5 — Management UI

### 범위

- Registry
- Runtime Artifact
- Master Agent Endpoint
- Execution/Trace
- Runtime/P Region 관제

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P5-001 | Source Group UI | UI/API/MASTER_AGENT 필터/표시 |
| P5-002 | Registry UI | Component/Version 조회·관리 |
| P5-003 | Artifact UI | Runtime Artifact 연결 확인 |
| P5-004 | Endpoint UI | Master Agent WAS 주소 관리 |
| P5-005 | Execution UI | 결과 이력 표시 |
| P5-006 | Trace UI | Step 없음 케이스 지원 |
| P5-007 | Runtime Dashboard | Master/P Region 지표 표시 |

### 제거

- Queue Dashboard
- Worker Dashboard
- Lease Monitor
- Policy/Rule/Governance UI

## 8. Phase 6 — 배포/HA/관제

### 범위

- OCP/Kubernetes
- Runtime Artifact 배포
- Master Agent WAS HA
- Probe/PDB/Topology
- Endpoint 전환/복구
- Metrics/Alert

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P6-001 | OCP Manifests | 현재 실제 배포 대상 반영 |
| P6-002 | Replica/PDB/Topology | 장애 시 서비스 지속 |
| P6-003 | Probe | Readiness/Liveness 검증 |
| P6-004 | NetworkPolicy | 허용 경로 최소화 |
| P6-005 | Runtime Artifact 검증 | 버전/Digest 일치 |
| P6-006 | Master Agent HA | 단일 WAS 장애 대응 |
| P6-007 | Endpoint 전환 | 검증된 주소만 운영 반영 |
| P6-008 | Rollback | 직전 정상 Runtime 복원 |
| P6-009 | Metrics/Alert | P Region/DB/Master 장애 탐지 |

## 9. Phase 7 — 수용/장애 시험

### Task

| ID | 작업 | 완료조건 |
|---|---|---|
| P7-001 | E2E | Customer→Master→P→execution 성공 |
| P7-002 | No Pre-Execution | 결과 전 execution 0건 |
| P7-003 | Trace Optional | Trace 유무 모두 정상 |
| P7-004 | Master Kill | HA 동작 |
| P7-005 | P Timeout | Blind Retry 없음 |
| P7-006 | DB Failure | 외부 중복 실행 없음 |
| P7-007 | Security | 주요 보안결함 0건 |
| P7-008 | Regression | 금지 구조 도입 0건 |

## 10. Definition of Done

- ERD v1.2 정합성 검증 완료
- UI/API/MASTER_AGENT Source Group만 사용
- Master Agent Registry→Version→Runtime Artifact 구조 적용
- WAS 주소는 master_agent_endpoint 사용
- 요청 시작 시 execution 생성 0건
- 결과 수신 후 execution 저장
- Structured Trace 없을 때 execution_step 0건
- Worker/Queue/Lease/Heartbeat 코드·테이블 사용 0건
- Policy/Rule/Governance 코드·테이블 사용 0건
- 승인 없는 스키마/상태값 변경 0건

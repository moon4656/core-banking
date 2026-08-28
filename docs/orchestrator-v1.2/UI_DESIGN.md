# UI_DESIGN — Management Portal (ERD v1.2 Baseline)

## 1. UI 설계 원칙

- 메뉴와 화면은 ERD v1.2에서 실제 관리하는 리소스만 노출한다.
- Worker/Queue/Lease/Heartbeat 관리 화면을 만들지 않는다.
- Policy/Rule/Governance 메뉴를 만들지 않는다.
- Source Group은 UI/API/MASTER_AGENT 세 값으로만 표현한다.
- Master Agent Version/Artifact와 Endpoint를 분리해 보여준다.
- execution_step은 존재하지 않을 수 있음을 기본 UX로 처리한다.

## 2. 권고 메뉴 구조

```text
Dashboard
├─ Runtime 현황
├─ Master Agent 현황
├─ P Region 연계 현황
└─ 배포 현황

Registry
├─ Components
├─ Versions
├─ Runtime Artifacts
└─ Master Agent Endpoints

Runtime
├─ Executions
└─ Execution Trace

Administration
├─ 사용자/권한 (ERD v1.2 범위)
└─ Audit (ERD v1.2 범위)
```

ERD v1.2 원문에 별도 확정 관리 메뉴가 존재한다면 추가할 수 있으나, 본 문서에서 테이블을 추정해 메뉴를 늘리지 않는다.

## 3. Dashboard

권고 KPI:

- Master Agent 호출 성공/실패
- Master Agent 응답시간
- P Region 호출 성공/실패
- P Region Timeout
- Circuit Open 여부/횟수
- execution 저장 성공/실패
- Structured Trace 수신 비율
- 배포/Health 상태

제거 KPI:

- Queue Depth
- Oldest Queue Age
- Claimed Worker
- Lease Expired
- Heartbeat
- RETRY_WAIT

## 4. Registry Component 화면

목록 표시:

- Component 식별정보
- Source Group: UI/API/MASTER_AGENT
- 최신/활성 Version 정보(ERD v1.2 범위)

필터:

```text
ALL / UI / API / MASTER_AGENT
```

Source Group 임의 입력은 허용하지 않는다.

## 5. Registry Version 화면

- Component별 Version 목록
- 승인 상태/활성 상태는 ERD v1.2 정의에 따라 표시
- Runtime Artifact 연결정보 표시
- 승인된 Version의 직접 수정은 기존 승인 정책에 따라 제한

## 6. Runtime Artifact 화면

- Registry Version과 연결된 Artifact Version 표시
- Image/Artifact/Digest 등은 ERD v1.2에 실제 존재하는 필드만 표시
- Master Agent일 경우 Endpoint와 Artifact를 같은 필드처럼 보이지 않게 구분

## 7. Master Agent Endpoint 화면

Master Agent 전용 관리 화면.

표시:

- Master Agent Component/Version 참조 정보
- WAS Endpoint 정보
- 현재 사용 여부/검증 정보는 ERD v1.2 컬럼이 존재하는 범위에서 표시

운영 버튼:

- 등록/수정/활성 등은 백엔드에서 ERD v1.2 규칙을 재검증
- URL 직접 입력만으로 즉시 운영 반영하지 않도록 권한/검증 절차 적용

## 8. Execution 화면

목록 의미:

- 완료 또는 결과가 수신되어 저장된 실행 이력
- Queue 대기/Worker 처리 목록이 아님

표시 필드는 ERD v1.2 실제 컬럼만 사용한다.

삭제할 기존 표시:

- Claimed Worker
- Lease Expires
- Retry Scheduler
- Queue Position

## 9. Execution 상세

권고 탭:

```text
1. Request/Execution Summary
2. Master Agent 정보
3. P Region Leader 정보
4. Result
5. Structured Trace
6. Audit/Correlation (지원 시)
```

Structured Trace 탭:

- execution_step이 있으면 Step 목록 표시
- 없으면 “P Region Structured Trace 미제공” 상태로 표시
- Step을 UI에서 추정 생성하지 않는다.

## 10. 제거 화면

현재 기준에서 제거한다.

- Execution Worker 화면
- Queue Monitor
- Lease/Heartbeat Monitor
- Recovery/Retry Scheduler
- Policy/Rule 화면
- Governance Check 화면

## 11. 오류 UX

주요 표시:

- Master Agent Endpoint 연결 실패
- P Region Timeout
- P Region 결과 오류
- execution 저장 실패

오류를 Queue 상태 또는 가상의 execution 상태로 변환해 표시하지 않는다.

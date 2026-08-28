# DATA_MODEL — ERD v1.2 적용 기준

## 1. 최우선 원칙

이 문서는 **ERD v1.2**를 최신 확정 데이터 모델로 취급한다.

- 구버전 v1.3/v1.5 문서의 테이블·컬럼·상태값을 v1.2에 자동 적용하지 않는다.
- 본 문서는 현재 대화에서 확정된 v1.2 관계만 명시한다.
- 전체 물리 컬럼 목록은 ERD v1.2 원문을 그대로 따른다.
- 미확인 컬럼·FK·상태값은 추정하지 않는다.

## 2. 확정 Source Group

```text
UI
API
MASTER_AGENT
```

Source Group에 네 번째 값을 임의 추가하지 않는다.

## 3. Registry 핵심 관계

현재 확정 관계:

```text
registry_component
  1
  └─ N registry_version
          └─ runtime_artifact_version
```

Master Agent 또한 이 관계를 사용한다.

### 3.1 registry_component

역할:

- 논리 Component 식별
- UI/API/MASTER_AGENT Source Group 분류의 기준

물리 컬럼은 ERD v1.2 원문을 따른다.

### 3.2 registry_version

역할:

- Component의 버전 단위 관리
- 승인/활성 등 상태는 ERD v1.2 승인 값 사용

### 3.3 runtime_artifact_version

역할:

- Registry Version에 대응하는 실제 Runtime Artifact 버전 관리
- 배포 Artifact/Digest 등 물리 속성은 ERD v1.2 정의에 한정

## 4. Master Agent Endpoint

확정 테이블:

```text
master_agent_endpoint
```

역할:

- Master Agent의 실제 WAS 주소 관리
- Runtime Artifact의 Version 정보와 실제 네트워크 Endpoint 역할 분리

원칙:

- Endpoint를 `runtime_artifact_version`에 임의 컬럼으로 추가하지 않는다.
- `master_agent_endpoint`의 정확한 FK/컬럼/상태는 ERD v1.2 원문을 따른다.
- 다중 Endpoint, 우선순위, 활성 플래그 등이 ERD에 명시되지 않았다면 문서에서 임의 정의하지 않는다.

## 5. Execution

확정 테이블:

```text
execution
execution_step
```

### 5.1 execution 의미

현재 프로젝트에서 `execution`은 사전 Queue/작업 상태 레코드가 아니라 **Master Agent가 P Region Leader 실행 결과를 받은 후 저장하는 실행 결과 이력**이다.

저장 시점:

```text
Customer Request
→ Master Agent
→ P Region Leader
→ Result
→ execution INSERT
```

금지:

```text
Request
→ execution QUEUED INSERT
→ Worker Claim
```

### 5.2 execution 상태값

본 문서에서는 신규 상태값을 정의하지 않는다.

- ERD v1.2 승인 상태값만 사용한다.
- 구버전 문서의 `QUEUED`, `PROCESSING`, `RETRY_WAIT` 등을 현재 v1.2에 자동 승계하지 않는다.
- 상태값 변경이 필요하면 ERD 변경 승인을 먼저 받는다.

## 6. execution_step

저장 조건:

```text
P Region Structured Trace 제공 = YES
  → execution_step 저장 가능

P Region Structured Trace 제공 = NO
  → execution_step 저장하지 않음
```

원칙:

- K Region 내부 처리 단계를 Step으로 합성하지 않는다.
- Trace의 Step 구조가 ERD v1.2와 맞지 않으면 컬럼을 추가하지 않는다.
- Mapping 불가 항목은 Contract/ERD 변경 검토 대상으로 남긴다.

## 7. 제거/비사용 구조

현재 프로젝트에서 사용하지 않는다.

### 7.1 Worker/Queue 계열

- execution-worker 전제
- Queue Table/Queue State
- Claim
- Lease
- Heartbeat
- Lease Recovery
- Retry Scheduler
- Worker Ownership 상태

기존 execution에 관련 컬럼이 ERD v1.2에 실제 존재하는지는 원문을 대조하되, 존재하더라도 현재 Runtime 제어 설계에 임의 사용하지 않는다.

### 7.2 Policy/Rule/Governance 계열

다음 논리 구조는 현재 프로젝트에서 사용하지 않는다.

- Policy
- Policy Rule
- Governance Check
- Policy Version 연결구조

구버전 DATA_MODEL에 있던 관련 테이블을 v1.2 구현 기준으로 사용하지 않는다.

## 8. 기타 ERD v1.2 테이블

사용자/권한, 서비스/환경, P Region, Leader, Release/Deployment, Audit, Memory 등의 전체 테이블 목록과 관계는 **ERD v1.2 원문이 제공하는 경우 그 정의를 그대로 따른다.**

현재 자료만으로 v1.2 전체 물리 목록을 확정할 수 없으므로 이 문서에서 임의 재구성하지 않는다.

## 9. 변경 통제

다음 변경은 코드 또는 Migration보다 먼저 승인해야 한다.

- 신규 테이블
- 신규 컬럼
- FK 관계 변경
- 테이블명 변경
- 상태값 추가/삭제/이름변경
- Source Group 값 추가
- execution 저장 시점 변경
- execution_step 생성 조건 변경

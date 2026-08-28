# CONSISTENCY CHECK — ERD v1.2 Document Set

## 1. 공통 불변 규칙

| 불변 규칙 | PRD | TECH | ARCH | DATA | API | UI | DEPLOY | TEST | TASK |
|---|---|---|---|---|---|---|---|---|---|
| ERD v1.2 최우선 | O | O | O | O | O | O | O | O | O |
| Source Group = UI/API/MASTER_AGENT | O | O | O | O | O | O | O | O | O |
| 요청 시작 시 execution 미생성 | O | O | O | O | O | O | N/A | O | O |
| P 결과 후 execution 저장 | O | O | O | O | O | O | N/A | O | O |
| Trace 있을 때만 execution_step | O | O | O | O | O | O | N/A | O | O |
| Worker/Queue/Lease/Heartbeat 미사용 | O | O | O | O | O | O | O | O | O |
| Policy/Rule/Governance 미사용 | O | O | O | O | O | O | O | O | O |
| Master Agent Registry→Version→Artifact | O | O | O | O | O | O | O | O | O |
| WAS 주소 = master_agent_endpoint | O | O | O | O | O | O | O | O | O |
| 신규 스키마/상태 임의 추가 금지 | O | O | O | O | O | O | O | O | O |

## 2. 구버전 충돌 제거 확인

제거/비활성화한 전제:

- ERD v1.5 기준선
- execution QUEUED 사전 생성
- execution-worker
- PostgreSQL SKIP LOCKED Queue
- Claim/Lease/Heartbeat/Worker Recovery
- PROCESSING/RETRY_WAIT 중심 상태 머신을 실행제어에 사용
- Policy/Rule/Governance 구조
- Structured Trace 없는 execution_step 합성
- v1.5 Canary 확장 컬럼/상태 전제

## 3. 문서 간 의존성

```text
PRD        : 무엇을 만들지 확정
TECH_SPEC  : PRD를 구현 규칙으로 변환
ARCHITECTURE: TECH의 책임/호출 경계 확정
DATA_MODEL : ARCH에서 사용하는 데이터만 ERD v1.2 범위로 제한
API_SPEC   : DATA_MODEL 밖의 필드/상태를 생성하지 않음
UI_DESIGN  : API/DATA에 없는 운영 개념을 화면에 추가하지 않음
DEPLOYMENT : Runtime Artifact와 Endpoint를 분리해 운영
TEST_PLAN  : 위 불변 규칙을 수용 테스트로 검증
TASK       : TEST_PLAN으로 검증 가능한 순서로 구현 Phase 구성
```

## 4. 구현 전 반드시 원문 대조가 필요한 항목

- runtime_artifact_version 물리 컬럼/FK
- master_agent_endpoint 물리 컬럼/FK/상태
- execution의 ERD v1.2 실제 컬럼/상태
- execution_step의 실제 Trace 매핑 컬럼
- P Region Execute/Status/Health/Structured Trace Contract
- ERD v1.2의 배포/이력 관련 정확한 물리 모델

이 항목들은 문서에서 의도적으로 추정하지 않았다.

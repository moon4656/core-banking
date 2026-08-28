# DEPLOYMENT — OCP/Kubernetes + Runtime Artifact (ERD v1.2 Baseline)

## 1. 배포 원칙

- 배포 데이터 모델은 ERD v1.2를 기준으로 한다.
- 구버전 v1.5 Canary 확장 컬럼/상태를 자동 적용하지 않는다.
- Runtime Artifact Version과 실제 Master Agent Endpoint를 분리 관리한다.
- Worker/Queue 복구를 위한 배포 절차는 사용하지 않는다.

## 2. 배포 대상 분류

Source Group:

```text
UI
API
MASTER_AGENT
```

각 배포 대상은 Registry Component/Version과 Runtime Artifact Version으로 식별한다.

Master Agent는 추가로 `master_agent_endpoint`를 통해 실제 WAS 주소를 관리한다.

## 3. Master Agent 배포 흐름

논리 흐름:

```text
registry_component
→ registry_version
→ runtime_artifact_version
→ 배포
→ Health 검증
→ master_agent_endpoint 운영 연결
```

Endpoint 등록/전환 상세 상태값은 ERD v1.2 정의를 따른다.

## 4. OCP/Kubernetes HA

Worker가 없더라도 Runtime 자체의 가용성은 필요하다.

권고:

- 외부 요청 API: 2 Replica 이상
- 관리 API: 2 Replica 이상(운영 중요도에 따라)
- Master Agent Runtime: WAS/LB 또는 Kubernetes Service 수준 HA
- PDB
- Anti-affinity 또는 Topology Spread
- Readiness/Liveness Probe
- HPA는 CPU/Memory 또는 실제 요청 지표 기반

Queue Depth/Worker Throughput 기반 HPA는 사용하지 않는다.

## 5. Probe

Readiness는 Process 생존뿐 아니라 최소한의 필수 Dependency 접근 가능성을 확인하되, 외부 P Region 전체 장애 때문에 K Region Pod 전체를 무조건 NotReady로 만드는 설계는 피한다.

예:

| 대상 | Readiness | Liveness |
|---|---|---|
| API | 필수 DB/Config 접근 | Process |
| Management API | DB/Registry 접근 | Process |
| Master Agent | Runtime 초기화/필수 설정 | Process |

P Region 연결 상태는 별도 Health/Metric으로 관제하는 편이 안전하다.

## 6. 네트워크/보안

- Default Deny NetworkPolicy 권고
- 허용된 API ↔ Master Agent 통신
- Master Agent ↔ P Region 통신
- 관리 API ↔ DB/배포 시스템
- Secret은 Secret Manager/K8s Secret 등 기존 체계 사용
- 고객 Token을 P Region에 전달하지 않는다.

## 7. 배포 검증

배포 전후 최소 검증:

1. 대상 Registry Version 승인 여부
2. Runtime Artifact Version 일치 여부
3. Artifact Digest/버전 검증(ERD v1.2 지원 범위)
4. Master Agent Health
5. Endpoint 연결 검증
6. P Region 기본 Health/Contract 검증
7. 주요 요청 Smoke Test

## 8. 장애/롤백

현재 프로젝트에서 중요한 배포 복원력:

```text
신규 Runtime 배포
→ Health 실패 또는 호출 오류
→ 신규 Runtime 사용 중단
→ 직전 정상 Runtime/Endpoint 복원
```

정확한 Rollback 상태/이력 테이블은 ERD v1.2 정의를 사용한다. 구버전 `deployment_history` Canary 전용 컬럼을 임의 추가하지 않는다.

## 9. 종료 처리

Worker Queue Drain은 존재하지 않는다.

일반 API/Master Agent Runtime은:

- SIGTERM 수신
- 신규 요청 수락 중단
- 진행 중 HTTP 요청에 Grace Period 적용
- 종료

정도로 처리한다.

## 10. 배포 금지사항

- Worker Deployment 추가
- Queue 지표 기반 Worker HPA
- Lease 만료 복구 전제 Rolling Update
- v1.5 Canary 컬럼을 v1.2 DB에 임의 추가
- Artifact Version과 Endpoint 역할 혼합
- Health 확인 없이 Endpoint 운영 전환

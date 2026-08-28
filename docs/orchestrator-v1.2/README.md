# ERD v1.2 문서 세트 — Current Project Baseline

읽는 순서:

1. PRD.md
2. TECH_SPEC.md
3. ARCHITECTURE.md
4. DATA_MODEL.md
5. API_SPEC.md
6. UI_DESIGN.md
7. DEPLOYMENT.md
8. TEST_PLAN.md
9. TASK.md

## 공통 고정 기준

- ERD v1.2가 최우선 기준
- Source Group = UI / API / MASTER_AGENT
- 요청 시작 시 execution 미생성
- Master Agent → P Region Leader 결과 수신 후 execution 저장
- execution_step = P Region Structured Trace가 있을 때만
- Worker/Queue/Lease/Heartbeat 미사용
- Policy/Rule/Governance 미사용
- Master Agent = registry_component → registry_version → runtime_artifact_version
- WAS 주소 = master_agent_endpoint
- 승인 없는 테이블/컬럼/관계/상태값 변경 금지

## 구버전 문서에서 제거한 핵심 충돌

- ERD v1.5 기준 표기
- execution QUEUED 사전 생성
- execution-worker
- PostgreSQL Queue/Claim
- Lease/Heartbeat/Recovery
- PROCESSING/RETRY_WAIT 중심 상태 머신 전제
- Policy/Rule/Governance 구조
- Structured Trace 없이 K Region이 Step 합성
- v1.5 Canary 확장 전제

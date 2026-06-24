---
name: restore-phase
description: >
  /compact 이후 반드시 실행되는 복원 스킬.
  COMPACT_READY.md를 먼저 읽고
  현재 단계와 다음 실행 단계를 복원한다.
  복원 없이 다음 단계 진행을 금지한다.
  /compact 이후, context 복원,
  phase restore 요청 시 활성화.
---

# Rules

1. FIRST read:
.sdd/context/COMPACT_READY.md

2. Restore:
- current phase
- completed work
- important decisions
- pending issues
- next exact step

3. STOP

4. Wait for approval

Never continue automatically.

If COMPACT_READY.md does not exist:

STOP

Output:
WARNING: .sdd/context/COMPACT_READY.md not found

- .sdd/context/COMPACT_READY.md 먼저 읽고
- 현재 단계와 다음 실행 단계를 복원한다.
- 복원 없이 다음 단계 진행을 금지한다.

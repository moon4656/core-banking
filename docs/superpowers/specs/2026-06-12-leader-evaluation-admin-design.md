# Leader Evaluation Admin UI Design

## Goal

관리자 화면에서 리더 Agent 평가 데이터를 목록과 상세 패널로 빠르게 조회할 수 있도록 한다.

## Scope

- 신규 관리자 메뉴 `리더 평가` 추가
- 신규 페이지 `/admin/leader-evaluations` 추가
- 목록 조회 API `GET /api/v1/admin/leader-evaluations` 연동
- 상세 조회 API `GET /api/v1/admin/leader-evaluations/{request_id}` 연동

## Design

기존 [analysis/traces](/c:/temp/core-banking/frontend/src/app/analysis/traces/page.tsx) 화면 패턴을 재사용한다. 상단에는 요청 목록과 기본 필터를 두고, 선택된 요청에 대한 요약 카드를 함께 배치한다. 하단에는 세부 정보를 카드 단위로 나누어 `리더 판단`, `Trace Events`, `Evidence`를 동시에 보여준다.

## Data Handling

- 목록은 `request_id`, 질문, intent, agent, confidence, overall result 중심으로 보여준다.
- 상세는 선택된 `request_id` 기준으로만 조회한다.
- 아직 백엔드에 저장되지 않은 `expected_*`, `reviewer`, `hallucination_yn`, `answer` 같은 필드는 `-` 또는 안내 문구로 표시한다.

## Error Handling

- 목록/상세 조회 실패 시 기존 패턴대로 `Alert`로 표시한다.
- 상세 선택 전에는 빈 상태 메시지를 보여준다.

## Testing

- TypeScript 빌드로 타입 정합성 확인
- Docker frontend 빌드로 실제 라우트 포함 여부 확인

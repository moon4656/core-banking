# Session Token Hardening Design

## Goal

현재 포털의 서명 토큰 기반 인증을 유지하되, 운영 포털에 맞는 보안성과 사용성을 확보한다.

이번 설계 범위는 아래 네 가지다.

- 세션 토큰 만료 시간을 30분으로 고정
- 만료 시 즉시 로그인 화면으로 이동
- 만료 메시지를 사용자에게 명확하게 안내
- `SESSION_SECRET`를 환경변수 기반 운영 설정으로 정리

## Chosen Approach

무상태 서명 토큰 방식을 유지하고, 리프레시 토큰이나 서버 세션 저장소는 도입하지 않는다.

이 선택의 이유는 다음과 같다.

- 현재 코드 구조와 가장 잘 맞는다.
- 백엔드 변경 범위가 작고, 기존 인증 흐름을 크게 깨지 않는다.
- 운영 포털 MVP 단계에서 필요한 보안 강화는 충분히 달성할 수 있다.
- 이후 JWT/OAuth2 또는 서버 세션 저장소로 확장할 여지도 남겨둔다.

## Rejected Alternatives

### 1. 리프레시 토큰 추가

장점:

- 사용자 재로그인 빈도를 줄일 수 있다.

단점:

- 토큰 수명 관리, 갱신 정책, 저장 위치를 추가 설계해야 한다.
- 현재 MVP 포털에는 복잡도가 크다.

### 2. 서버 세션 저장소 또는 블랙리스트 추가

장점:

- 강제 로그아웃, 토큰 폐기, 중앙 제어가 쉬워진다.

단점:

- Redis 또는 DB 기반 세션 상태 관리가 필요하다.
- 현재 무상태 구조를 크게 바꾸게 된다.

## Authentication Flow

### Login

1. 사용자가 `X-API-Key`와 사용자명을 입력한다.
2. 프론트가 `POST /api/v1/auth/login`을 호출한다.
3. 백엔드는 API Key를 검증하고 역할을 결정한다.
4. 백엔드는 30분 만료의 서명 토큰을 발급한다.
5. 프론트는 `access_token`, `token_type`, `role`, `name`, `auth_mode`를 로컬 세션에 저장한다.

### Protected Screen Access

1. 사용자가 보호 화면으로 이동한다.
2. 프론트 `AppShell`이 `GET /api/v1/auth/me`를 `Authorization: Bearer <token>`으로 호출한다.
3. 백엔드는 토큰 서명과 만료 시간을 검증한다.
4. 유효하면 세션 정보를 반환한다.
5. 무효하거나 만료되면 401을 반환한다.

### Expiration Handling

1. 프론트가 `auth/me` 또는 일반 API 호출에서 401을 받는다.
2. 프론트는 로컬 세션을 삭제한다.
3. 로그인 화면으로 즉시 이동한다.
4. 로그인 화면에 `세션이 만료되었습니다. 다시 로그인해 주세요.` 메시지를 표시한다.

## Backend Changes

### Security

`backend/app/core/security.py`

- 서명 토큰 발급과 검증 유지
- 만료 시간은 `SESSION_TTL_SECONDS=1800` 기준으로 사용
- 보호 API는 `Bearer`를 우선 사용
- `Bearer`가 없을 때만 기존 `X-API-Key` fallback 허용 여부를 명확히 정리

권장 방향:

- 일반 포털 UI 경로는 Bearer 사용
- 개발/Swagger/운영 점검용으로만 `X-API-Key` fallback 유지

### Config

`backend/app/core/config.py`

- `SESSION_SECRET`
- `SESSION_TTL_SECONDS=1800`

추가 원칙:

- 기본값은 개발용으로만 사용
- 운영에서는 `.env` 또는 컨테이너 환경변수에서 반드시 주입

### Auth API

`backend/app/api/routes/auth.py`

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

추가 변경:

- `401` 응답 메시지를 세션 만료와 인증 실패 관점에서 더 명확히 정리

## Frontend Changes

### Session Storage

`frontend/src/lib/session.ts`

- `accessToken`
- `tokenType`
- `role`
- `name`
- `authMode`

### API Client

`frontend/src/lib/api.ts`

- 일반 API 호출 시 `Authorization: Bearer <token>` 사용
- 401 처리 유틸 추가 후보:
  - 전역 핸들링
  - 각 페이지 공통 처리

권장 방향:

- 우선 `AppShell`에서 보호 화면 진입 시 검증
- 이후 필요하면 공통 401 핸들러로 확장

### Login Screen

`frontend/src/app/login/page.tsx`

- 사용자명과 API Key 입력
- 서버 검증 성공 시 세션 저장
- 실패 시 로그인 오류 표시
- 리다이렉트된 만료 진입이면 만료 메시지 표시

### Protected Layout

`frontend/src/components/layout/AppShell.tsx`

- 진입 시 `auth/me` 호출
- 401이면 세션 삭제
- 로그인 화면으로 이동
- `?reason=expired` 같은 쿼리 파라미터로 만료 이유 전달

### Topbar

`frontend/src/components/layout/Topbar.tsx`

- 현재 사용자명
- 역할
- auth mode 표시 유지 가능
- 로그아웃 시 세션 삭제 후 로그인 이동

## Error Handling

### Invalid Login

- 메시지: `유효하지 않은 인증 정보입니다.`

### Expired Session

- 메시지: `세션이 만료되었습니다. 다시 로그인해 주세요.`

### Missing Session

- 메시지 없이 로그인 화면으로 이동하거나, 동일한 만료 메시지로 통일 가능

권장 방향:

- `missing`과 `expired`를 모두 로그인 재진입으로 처리
- 사용자 메시지는 `expired`일 때만 적극 표시

## Testing

### Backend

- 로그인 성공 시 토큰 발급
- 만료 전 `auth/me` 성공
- 잘못된 토큰 401
- 만료된 토큰 401
- 보호 API가 Bearer 토큰으로 정상 동작

### Frontend

- 로그인 성공 후 대시보드 이동
- 보호 화면 진입 시 `auth/me` 성공
- 만료/401 시 로그인 화면 이동
- 만료 메시지 표시

## Risks

### 1. 완전한 강제 로그아웃 불가

무상태 토큰 구조에서는 이미 발급된 토큰을 서버가 즉시 폐기하기 어렵다.

완화:

- 만료 시간을 30분으로 짧게 유지

### 2. 브라우저 저장소 보안 한계

토큰을 로컬 저장소에 저장하면 XSS에 취약할 수 있다.

완화:

- 입력/출력 sanitization 강화
- 향후 `httpOnly cookie` 또는 서버 세션 방식 검토

### 3. 운영 환경 비밀키 관리

`SESSION_SECRET` 기본값이 운영에 남아 있으면 위험하다.

완화:

- 운영 배포 시 환경변수 필수화
- 문서와 배포 설정에 명확히 반영

## Scope Boundary

이번 설계에 포함하지 않는 항목:

- 리프레시 토큰
- JWT/OAuth2 표준 프로토콜 전환
- 서버 세션 저장소
- 토큰 폐기 블랙리스트

## Implementation Recommendation

구현 순서는 아래가 적절하다.

1. 백엔드 테스트 추가
2. 백엔드 만료/응답 로직 보강
3. 프론트 로그인/세션 만료 UX 반영
4. 문서와 환경변수 예시 업데이트

# PRD.md

# Docker 기반 멀티에이전트 AI 서비스 MVP PRD

작성일: 2026-06-09

---

## 1. 문서 목적

본 문서는 Docker Compose 기반 로컬/사내 개발 환경에서 동작 가능한 **멀티에이전트 AI 서비스 MVP**의 제품 요구사항을 정의한다.

본 MVP는 정식 온톨로지, Graph DB, RDF/OWL, SPARQL 구축을 목표로 하지 않는다. 대신 향후 온톨로지 및 Graph RAG 확장이 가능하도록 **PostgreSQL 기반 경량 업무 지식 모델**, **Agent 실행 구조**, **Tool/API Hub**, **Trace/Evidence 저장 구조**를 우선 구축한다.

---

## 2. 배경

AI Agent 서비스는 단순 챗봇과 달리 다음 요구가 존재한다.

- 사용자 질문에 따라 적절한 Agent를 선택해야 한다.
- Agent가 내부 API, 문서, Mock 데이터 등을 통제된 방식으로 사용해야 한다.
- Agent 실행 과정과 근거 데이터가 추적 가능해야 한다.
- 향후 온톨로지, Graph RAG, 리니지, 권한 기반 검색으로 확장 가능해야 한다.
- 초기 MVP에서는 범위를 통제하기 위해 정식 온톨로지 구축을 제외해야 한다.

따라서 본 MVP는 **온톨로지 구축이 아닌, 온톨로지로 확장 가능한 경량 업무 지식 모델**을 개발 범위로 한다.

---

## 3. 핵심 방향

### 3.1 포함 방향

- Docker Compose 기반 로컬 실행
- FastAPI 기반 Backend
- PostgreSQL 기반 메타데이터/Trace 저장
- Redis 기반 세션/캐시/비동기 큐 확장 준비
- Leader Agent 기반 Orchestration
- Sub Agent 2~3개 수준의 MVP
- Tool/API Hub를 통한 Mock API 호출
- 업무 개념, Agent, API, Data Source 매핑
- Trace/Event 저장
- Evidence/근거 저장
- 향후 Graph RAG/온톨로지 확장 고려

### 3.2 제외 방향

- 정식 온톨로지 구축
- Neo4j / Graph DB 운영
- RDF / OWL / SPARQL
- 전사 업무 용어 표준화
- 모든 DB 컬럼 매핑
- 모든 규정 문서 구조화
- 코어뱅킹 실거래 API 직접 연계
- 자동 관계 추론 엔진
- 운영용 Kubernetes 배포

---

## 4. 목표

### 4.1 제품 목표

사용자가 질문을 입력하면 Leader Agent가 질문의 핵심 업무 개념을 식별하고, 해당 개념에 맞는 Sub Agent와 Tool/API를 선택하여 답변을 생성한다. 모든 실행 과정은 Trace와 Evidence로 저장되어 향후 감사, 품질평가, 리니지, Graph RAG 확장에 활용할 수 있어야 한다.

### 4.2 MVP 성공 기준

- Docker Compose 한 번으로 전체 서비스 실행 가능
- 사용자 질문 입력 API 제공
- Leader Agent가 업무 개념을 식별
- concept_id 기준으로 Agent 라우팅
- concept_id 기준으로 API/Tool 선택
- Mock API 또는 Mock 문서 검색 결과를 사용
- 최종 응답 생성
- 요청 단위 Trace 저장
- Agent 실행 단위 Trace 저장
- 응답 근거 Evidence 저장
- 관리자/개발자가 Trace/Evidence 조회 가능

---

## 5. 사용자 유형

| 사용자 | 설명 |
|---|---|
| 일반 사용자 | AI에게 업무 질문을 입력하는 사용자 |
| 업무 담당자 | 업무 용어, API, Agent 매핑을 검토하는 담당자 |
| AI 개발자 | Agent, Tool, Trace 로직을 개발하는 개발자 |
| 시스템 관리자 | Docker 환경, DB, 로그, 설정을 관리하는 관리자 |
| 분석/설계자 | 업무 개념, 데이터, API, Agent 관계를 설계하는 담당자 |

---

## 6. 주요 사용자 시나리오

### 6.1 대출 상품 문의 예시

사용자 질문:

> 개인신용대출 금리와 필요서류 알려줘.

처리 흐름:

1. Gateway가 요청을 수신한다.
2. Leader Agent가 질문을 분석한다.
3. Metadata Resolver가 다음 개념을 식별한다.
   - 개인신용대출
   - 금리
   - 필요서류
4. concept_id 기준으로 Agent를 선택한다.
   - Product Agent
   - Rate Agent
   - Policy Agent
5. Tool/API Hub가 Mock API를 호출한다.
6. 각 Agent 결과를 Leader Agent가 통합한다.
7. 최종 응답을 반환한다.
8. Trace/Evidence를 저장한다.

---

## 7. 기능 요구사항

### 7.1 AI Gateway

- 사용자 질문 수신
- request_id 생성
- session_id 관리
- Leader Agent 호출
- 최종 응답 반환
- 요청 단위 Trace 생성

주요 API:

```http
POST /api/v1/ai/chat
GET  /api/v1/ai/sessions/{session_id}
GET  /api/v1/ai/traces/{request_id}
```

---

### 7.2 Leader Agent / Orchestrator

Leader Agent는 다음 기능을 수행한다.

- 사용자 의도 분석
- 업무 개념 식별 요청
- 실행 계획 생성
- Agent 선택
- Tool/API 선택
- Sub Agent 실행 순서 제어
- 결과 통합
- 안전성/일관성 검토
- 최종 응답 생성
- Trace/Evidence 연결

---

### 7.3 Sub Agent

MVP 대상 Sub Agent는 다음으로 제한한다.

| Agent | 역할 |
|---|---|
| Product Agent | 상품 정보, 조건, 필요서류 안내 |
| Rate Agent | 금리, 우대금리, 금리 범위 안내 |
| Policy Agent | 규정, 약관, 제한조건, 유의사항 안내 |
| Search/RAG Agent | 문서/FAQ 검색 및 요약 |

초기 MVP에서는 2~3개 Agent만 활성화해도 된다.

---

### 7.4 Knowledge Metadata Service

정식 온톨로지 대신 PostgreSQL 기반 경량 업무 지식 모델을 제공한다.

기능:

- 업무 개념 관리
- 업무 용어/동의어 관리
- 개념 간 관계 관리
- 개념-데이터 매핑
- 개념-API 매핑
- 개념-Agent 매핑
- 권한/민감도 메타데이터 관리
- concept_id 기반 조회

주요 API:

```http
GET /api/v1/knowledge/concepts
GET /api/v1/knowledge/concepts/search?keyword=금리
GET /api/v1/knowledge/concepts/{concept_id}/agents
GET /api/v1/knowledge/concepts/{concept_id}/apis
GET /api/v1/knowledge/concepts/{concept_id}/data-sources
```

---

### 7.5 Tool/API Hub

Agent가 내부 API나 Mock API를 직접 호출하지 않고 Tool/API Hub를 통해 호출한다.

기능:

- API Catalog 조회
- Agent별 API 접근 권한 확인
- 입력 파라미터 검증
- Mock API 호출
- 응답 정규화
- Tool 호출 로그 저장
- Evidence 저장 연계

주요 API:

```http
GET  /api/v1/tools
POST /api/v1/tools/invoke
GET  /api/v1/tools/{tool_id}/logs
```

---

### 7.6 Trace/Evidence

모든 요청과 Agent 실행은 추적 가능해야 한다.

Trace 저장 항목:

- request_id
- session_id
- user_id
- agent_id
- event_type
- input_summary
- output_summary
- status
- started_at
- ended_at
- error_message

Evidence 저장 항목:

- request_id
- trace_id
- agent_id
- concept_id
- source_type
- source_id
- api_id
- document_id
- chunk_id
- confidence_score
- used_in_response

---

## 8. 비기능 요구사항

| 항목 | 요구사항 |
|---|---|
| 실행환경 | Docker Compose 기반 |
| DB | PostgreSQL |
| Cache/Queue | Redis |
| Backend | FastAPI |
| API 문서 | Swagger/OpenAPI 자동 제공 |
| 로그 | 구조화 로그 JSON 권장 |
| 보안 | 환경변수 기반 Secret 관리 |
| 확장성 | 향후 실제 API, RAG, Graph DB 확장 가능 |
| 관측성 | 로그, Trace 조회 가능 |
| 테스트 | 단위 테스트 및 API 테스트 포함 |

---

## 9. Docker 기준 서비스 구성

```text
docker-compose.yml
 ├ backend          : FastAPI API 서버
 ├ postgres         : 메타데이터/Trace 저장 DB
 ├ redis            : 캐시/세션/큐 확장 준비
 ├ pgadmin          : 개발용 DB 관리 UI
 └ mock-api         : 내부 시스템 Mock API
```

선택 서비스:

```text
 ├ admin-ui         : 관리자 화면
 ├ worker           : 비동기 작업 처리
 └ prometheus       : 모니터링 확장
```

---

## 10. 데이터 범위

MVP Seed 데이터는 다음 정도로 제한한다.

업무 개념:

- 고객
- 개인신용대출
- 대출상품
- 금리
- 우대금리
- 필요서류
- 약관
- 규정
- 상담이력
- 신청조건

Mock 데이터:

- 상품 목록
- 금리 안내
- 필요서류
- 약관/규정 요약
- FAQ 문서

---

## 11. 범위 통제 원칙

본 MVP에서는 다음 원칙을 따른다.

1. 온톨로지라는 명칭을 개발 범위명으로 사용하지 않는다.
2. Knowledge Metadata Service라는 이름으로 경량 모델만 구현한다.
3. LLM이 API 권한을 임의 판단하지 못하게 한다.
4. Agent 라우팅은 테이블 기반 매핑을 우선한다.
5. Evidence 없는 중요 응답은 제한한다.
6. Graph DB는 후속 고도화 대상으로 분리한다.
7. 실제 내부 시스템 연계 전 Mock API로 먼저 검증한다.

---

## 12. 향후 확장 로드맵

| 단계 | 내용 |
|---|---|
| 1차 MVP | PostgreSQL 기반 경량 업무 지식 모델 |
| 2차 확장 | 실제 API Read-only 연계 |
| 3차 확장 | 문서 RAG 및 권한 필터 강화 |
| 4차 확장 | 업무 개념 관계 고도화 |
| 5차 확장 | Graph RAG / Knowledge Graph 검토 |
| 6차 확장 | 정식 온톨로지 또는 Graph DB 도입 검토 |

---

## 13. 결론

본 MVP는 온톨로지를 직접 구축하지 않는다. 대신 Docker Compose 기반으로 실행 가능한 멀티에이전트 AI 서비스의 최소 기반을 만들고, PostgreSQL 기반 경량 업무 지식 모델을 통해 Agent, API, 데이터, 근거 이력을 연결한다.

이 접근은 업무 범위 확대를 막으면서도 향후 온톨로지, Graph RAG, 리니지, 권한 기반 검색으로 확장할 수 있는 현실적인 구조이다.

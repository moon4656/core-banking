# CLAUDE_CODEX_DOCKER_AI_AGENT_MVP_QUERY.md

# Claude / Codex 개발 질의서  
## Docker 기반 멀티에이전트 AI 서비스 MVP

작성일: 2026-06-09

---

## 0. 사용 목적

이 문서는 Claude Code 또는 Codex에게 Docker 기반 멀티에이전트 AI 서비스 MVP를 분석·설계·개발시키기 위한 질의서이다.

반드시 아래 첨부 문서를 먼저 읽고, 그 내용을 기준으로 작업해야 한다.

```text
1. AI_Agent_PRD.md
2. AI_Agent_TECH_SPEC.md
3. AI_Agent_TECH_SPEC_TASK.md
```

---

## 1. 핵심 전제

본 프로젝트는 **정식 온톨로지 구축 프로젝트가 아니다.**

다음 항목은 본 단계에서 제외한다.

```text
- Neo4j
- Graph DB
- RDF / OWL
- SPARQL
- 자동 온톨로지 생성
- 자동 관계 추론
- 전사 용어 표준화
- 모든 DB 컬럼 매핑
- 실제 코어뱅킹 실거래 API 연계
- Kubernetes 운영 배포
```

대신 본 단계에서는 다음을 구현한다.

```text
- Docker Compose 기반 로컬 MVP
- FastAPI Backend
- PostgreSQL 기반 경량 업무 지식 모델
- Redis 기반 세션/캐시/큐 확장 준비
- Leader Agent / Orchestrator
- Sub Agent 2~3개
- Tool/API Hub
- Mock API
- Trace/Event 저장
- Evidence/근거 저장
- concept_id 기반 Agent 라우팅
- concept_id 기반 Tool/API 선택
```

---

## 2. 가장 중요한 개발 원칙

아래 원칙을 반드시 지켜라.

```text
1. 온톨로지라는 이름으로 개발하지 말 것.
2. Knowledge Metadata Service라는 이름으로 경량 업무 지식 모델을 구현할 것.
3. LLM이 Agent와 API를 임의로 선택하지 않게 할 것.
4. Agent 라우팅은 business_concept, agent_concept_mapping 기반으로 할 것.
5. Tool/API 선택은 concept_api_mapping, api_catalog 기반으로 할 것.
6. Agent는 API를 직접 호출하지 않고 Tool/API Hub를 통해 호출할 것.
7. 모든 사용자 요청은 trace_event에 저장할 것.
8. 응답 근거는 evidence_reference에 저장할 것.
9. Mock API로 먼저 검증하고 실제 API 연계는 후속 단계로 분리할 것.
10. Docker Compose로 한 번에 실행 가능해야 할 것.
```

---

## 3. 요청 사항

너는 시니어 Python/FastAPI 아키텍트이자 멀티에이전트 AI 시스템 개발 리드다.

첨부된 `PRD.md`, `TECH_SPEC.md`, `TECH_SPEC_TASK.md`를 기준으로 다음을 수행해라.

---

# 작업 1. 문서 정합성 검토

## 요청

먼저 세 문서를 읽고 다음 관점에서 정합성을 검토해라.

```text
1. PRD 요구사항과 TECH_SPEC 설계가 맞는지
2. TECH_SPEC 설계와 TECH_SPEC_TASK 작업 단계가 맞는지
3. Docker Compose 기준으로 빠진 서비스가 있는지
4. DB 스키마에서 누락된 테이블이나 관계가 있는지
5. API 설계에서 빠진 Endpoint가 있는지
6. Trace/Evidence 저장 흐름이 충분한지
7. 온톨로지 제외 범위가 명확히 통제되어 있는지
8. MVP에서 과도한 범위가 포함되어 있지 않은지
9. 실제 개발 순서가 맞는지
10. Phase별 완료 조건이 검증 가능한지
```

## 출력 형식

```markdown
# 문서 정합성 검토 결과

## 1. 전체 판단
- 적합 / 보완 필요 / 위험 중 하나로 판단

## 2. 문서 간 불일치
| 항목 | 위치 | 문제 | 수정 제안 |
|---|---|---|---|

## 3. 누락 사항
| 구분 | 누락 내용 | 영향도 | 보완 방법 |
|---|---|---|---|

## 4. 과도한 범위
| 항목 | 이유 | 제외 또는 후속 분리 제안 |
|---|---|---|

## 5. 반드시 수정해야 할 사항
1.
2.
3.

## 6. 최종 권고
```

---

# 작업 2. 최종 개발 구조 제안

## 요청

문서 검토 후 Docker 기준으로 실제 개발할 프로젝트 구조를 제안해라.

반드시 다음 구조를 포함해야 한다.

```text
backend/
mock-api/
docker-compose.yml
.env.example
README.md
```

Backend 내부에는 다음 모듈이 포함되어야 한다.

```text
app/core
app/api/routes
app/agents
app/orchestrator
app/knowledge
app/tools
app/trace
app/models
app/schemas
app/seed
tests
alembic
```

## 출력 형식

```markdown
# 최종 프로젝트 구조

```text
프로젝트 구조를 tree 형식으로 작성
```

## 주요 디렉터리 설명
| 경로 | 역할 |
|---|---|
```

---

# 작업 3. Phase 0부터 순차 개발 계획 재정리

## 요청

`TECH_SPEC_TASK.md`의 Phase를 기준으로 하되, 실제 개발 실행 순서로 다시 정리해라.

각 Phase는 다음을 포함해야 한다.

```text
- 목표
- 선행 조건
- 작업 목록
- 생성/수정 파일
- 완료 조건
- 테스트 방법
- 다음 Phase로 넘어가기 위한 승인 기준
```

## 중요 조건

각 Phase 종료 후 다음 문서를 생성하도록 계획에 포함해라.

```text
docs/context/COMPACT_READY.md
docs/context/CONTEXT_RESTORE.md
docs/phase/PHASE_N_RESULT.md
```

## 출력 형식

```markdown
# Phase 기반 개발 계획

## Phase 0. ...
### 목표
### 선행 조건
### 작업 목록
### 생성/수정 파일
### 완료 조건
### 테스트 방법
### 승인 기준
```

---

# 작업 4. Phase 0 실행 질의서 작성

## 요청

이제 실제 개발을 시작하기 위한 **Phase 0 실행 질의서**를 작성해라.

Phase 0의 목적은 다음이다.

```text
- 프로젝트 기본 디렉터리 생성
- Docker Compose 구성
- FastAPI backend 기본 실행
- mock-api 기본 실행
- PostgreSQL, Redis, pgAdmin 구성
- health check endpoint 구현
- .env.example 작성
- README 초안 작성
```

## Phase 0 금지 범위

```text
- DB 모델 구현 금지
- Agent 구현 금지
- Knowledge Metadata Service 구현 금지
- Tool/API Hub 구현 금지
- Trace/Evidence 구현 금지
- 온톨로지/Graph DB 관련 구현 금지
- Phase 1 작업 선행 금지
```

## Phase 0 완료 조건

```text
docker compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8010/health
```

두 API가 정상 응답해야 한다.

## 출력 형식

```markdown
# Phase 0 실행 질의서

## 역할
## 반드시 읽을 문서
## 목표
## 작업 범위
## 금지 범위
## 생성 파일
## 실행 명령
## 완료 조건
## Phase 종료 시 생성 문서
## 다음 단계 안내
```

---

# 작업 5. Phase 1 실행 질의서 작성

## 요청

Phase 1 실행 질의서를 작성해라.

Phase 1의 목적은 다음이다.

```text
- SQLAlchemy 모델 작성
- Alembic 구성
- PostgreSQL 연결
- 경량 업무 지식 모델 테이블 생성
- Trace/Evidence 테이블 생성
```

## Phase 1 대상 테이블

```text
business_concept
business_term_alias
business_concept_relation
data_source_catalog
api_catalog
concept_data_mapping
concept_api_mapping
agent_catalog
agent_concept_mapping
trace_event
evidence_reference
```

## Phase 1 금지 범위

```text
- Seed 데이터 등록 금지
- API Router 구현 금지
- Agent 구현 금지
- Tool/API Hub 구현 금지
- Chat API 구현 금지
- Graph DB/Neo4j/RDF/OWL/SPARQL 구현 금지
```

## 출력 형식

```markdown
# Phase 1 실행 질의서

## 역할
## 반드시 읽을 문서
## 목표
## 작업 범위
## 금지 범위
## 생성/수정 파일
## DB 모델 기준
## Alembic 기준
## 실행 명령
## 완료 조건
## 테스트 방법
## Phase 종료 시 생성 문서
```

---

# 작업 6. 전체 Phase별 Claude/Codex 승인 프롬프트 작성

## 요청

Phase 0부터 Phase 10까지 각 Phase를 승인하고 실행할 때 사용할 수 있는 프롬프트를 작성해라.

중요하다.  
단순히 `승인: Phase N`만 쓰지 말고, 반드시 다음을 포함해라.

```text
- 수행 범위
- 금지 범위
- 완료 조건
- Phase 종료 문서 생성 조건
- 다음 Phase 자동 진행 금지
```

## 출력 형식

```markdown
# Phase별 승인 프롬프트

## Phase 0 승인 프롬프트
```text
...
```

## Phase 1 승인 프롬프트
```text
...
```
```

---

# 작업 7. Codex용 짧은 실행 프롬프트 작성

## 요청

Codex에 바로 넣을 수 있는 짧은 실행 프롬프트를 작성해라.

조건:

```text
- 긴 설명 없이 핵심만 포함
- PRD.md, TECH_SPEC.md, TECH_SPEC_TASK.md를 먼저 읽도록 지시
- Phase 0만 실행
- Phase 1 이상 작업 금지
- Docker 실행 검증 포함
```

## 출력 형식

```markdown
# Codex용 Phase 0 단기 실행 프롬프트

```text
...
```
```

---

# 작업 8. Claude용 상세 실행 프롬프트 작성

## 요청

Claude Code에 넣을 상세 실행 프롬프트를 작성해라.

조건:

```text
- 역할 부여
- 문서 읽기 순서 명시
- Phase 0만 수행
- 금지 범위 명시
- Docker 실행 검증 명시
- COMPACT_READY.md, CONTEXT_RESTORE.md, PHASE_0_RESULT.md 생성 요구
- 다음 Phase 자동 진행 금지
```

## 출력 형식

```markdown
# Claude Code용 Phase 0 상세 실행 프롬프트

```text
...
```
```

---

## 4. 최종 출력물

최종 답변은 다음 파일들을 생성하는 수준으로 정리해라.

```text
1. DOC_REVIEW_RESULT.md
2. FINAL_PROJECT_STRUCTURE.md
3. PHASE_DEVELOPMENT_PLAN.md
4. PHASE_0_EXECUTION_PROMPT.md
5. PHASE_1_EXECUTION_PROMPT.md
6. PHASE_APPROVAL_PROMPTS.md
7. CODEX_PHASE_0_PROMPT.md
8. CLAUDE_PHASE_0_PROMPT.md
```

실제 파일 생성이 가능하다면 위 파일명을 기준으로 생성해라.  
파일 생성이 어렵다면 각 문서 내용을 Markdown으로 출력해라.

---

## 5. 절대 금지 사항

아래 작업은 하지 마라.

```text
1. Phase 0 실행 중 Phase 1 이상 작업을 선행하지 마라.
2. 온톨로지 구축으로 범위를 확대하지 마라.
3. Neo4j, Graph DB, RDF/OWL, SPARQL을 도입하지 마라.
4. LLM이 API/권한을 임의 판단하는 구조로 만들지 마라.
5. Agent가 내부 API를 직접 호출하는 구조로 만들지 마라.
6. Trace/Evidence 저장을 후순위로 미루지 마라.
7. Kubernetes를 제안하지 마라.
8. 실제 코어뱅킹/내부 실거래 API 연계를 구현하지 마라.
9. 문서에 없는 임의 기능을 추가하지 마라.
10. 다음 Phase를 자동으로 진행하지 마라.
```

---

## 6. 최종 주의

이 프로젝트의 핵심은 온톨로지 구현이 아니다.

핵심은 다음이다.

```text
Docker Compose 기반 MVP
+ FastAPI
+ PostgreSQL
+ 경량 업무 지식 모델
+ Leader Agent
+ Tool/API Hub
+ Trace/Evidence
+ Mock API
```

반드시 범위를 통제하고, Phase 단위로 진행해라.

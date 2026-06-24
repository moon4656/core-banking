# Phase 1 실행 질의서

작성일: 2026-06-09

---

## 역할

너는 시니어 Python/FastAPI 아키텍트이다. Docker Compose 기반 멀티에이전트 AI 서비스 MVP의 Phase 1(DB 모델 및 Alembic 마이그레이션)을 담당한다.

---

## 반드시 읽을 문서

작업 시작 전 다음 문서를 순서대로 읽어라.

```text
1. docs/AI_Agent_TECH_SPEC.md  ← 7절(DB 설계), 8절(Trace/Evidence 설계) 집중
2. docs/AI_Agent_TECH_SPEC_TASK.md  ← Phase 1 항목 집중
3. docs/FINAL_PROJECT_STRUCTURE.md
4. docs/context/CONTEXT_RESTORE.md  ← Phase 0 결과 확인
5. CLAUDE.md
```

---

## 목표

경량 업무 지식 모델과 Trace/Evidence 저장을 위한 11개 테이블을 SQLAlchemy 모델로 작성하고 Alembic으로 PostgreSQL에 적용한다.

---

## 작업 범위

다음 파일만 생성/수정한다.

```text
backend/app/core/database.py
backend/app/models/__init__.py
backend/app/models/knowledge_model.py
backend/app/models/agent_model.py
backend/app/models/tool_model.py
backend/app/models/trace_model.py
backend/alembic.ini
backend/alembic/env.py
backend/alembic/script.py.mako
backend/alembic/versions/0001_initial_schema.py
```

---

## 금지 범위

Phase 1에서 절대 구현하지 않는다.

```text
- Seed 데이터 등록 금지 (데이터 insert 금지, 테이블 생성만)
- API Router 구현 금지
- Agent 구현 금지
- Knowledge Service 구현 금지
- Tool/API Hub 구현 금지
- Trace Service 구현 금지
- Chat API 구현 금지
- Graph DB / Neo4j / RDF / OWL / SPARQL 구현 금지
- Phase 2 이상 작업 선행 금지
```

---

## 생성/수정 파일 상세

### backend/app/core/database.py

```python
# SQLAlchemy 2.x 기반
# create_async_engine 또는 create_engine (동기 방식 우선)
# SessionLocal 팩토리
# Base = declarative_base()
# DATABASE_URL은 config.py에서 읽음
# get_db() 의존성 주입 함수
```

### backend/app/models/knowledge_model.py

다음 5개 테이블 모델 포함:

```text
BusinessConcept       → business_concept 테이블
BusinessTermAlias     → business_term_alias 테이블
BusinessConceptRelation → business_concept_relation 테이블
DataSourceCatalog     → data_source_catalog 테이블
ConceptDataMapping    → concept_data_mapping 테이블
```

### backend/app/models/agent_model.py

다음 2개 테이블 모델 포함:

```text
AgentCatalog          → agent_catalog 테이블
AgentConceptMapping   → agent_concept_mapping 테이블
```

### backend/app/models/tool_model.py

다음 2개 테이블 모델 포함:

```text
ApiCatalog            → api_catalog 테이블
ConceptApiMapping     → concept_api_mapping 테이블
```

### backend/app/models/trace_model.py

다음 2개 테이블 모델 포함:

```text
TraceEvent            → trace_event 테이블
EvidenceReference     → evidence_reference 테이블
```

---

## DB 모델 기준

TECH_SPEC.md 7절과 8절의 SQL 정의를 기준으로 SQLAlchemy 모델을 작성한다.

### 공통 규칙
- PK는 UUID 타입 사용 (`uuid.uuid4` 기본값)
- created_at은 `server_default=func.now()`
- updated_at은 `onupdate=func.now()` 포함 (해당 테이블만)
- FK는 `ForeignKey` + `relationship` 모두 정의
- `__tablename__`은 snake_case

### 주요 FK 관계
```text
business_term_alias.concept_id → business_concept.concept_id
business_concept_relation.source_concept_id → business_concept.concept_id
business_concept_relation.target_concept_id → business_concept.concept_id
concept_data_mapping.concept_id → business_concept.concept_id
concept_data_mapping.data_source_id → data_source_catalog.data_source_id
concept_api_mapping.concept_id → business_concept.concept_id
concept_api_mapping.api_id → api_catalog.api_id
agent_concept_mapping.agent_id → agent_catalog.agent_id
agent_concept_mapping.concept_id → business_concept.concept_id
trace_event.agent_id → agent_catalog.agent_id
evidence_reference.trace_id → trace_event.trace_id
evidence_reference.agent_id → agent_catalog.agent_id
evidence_reference.concept_id → business_concept.concept_id
evidence_reference.api_id → api_catalog.api_id
```

---

## Alembic 기준

### alembic.ini
- `script_location = alembic`
- `sqlalchemy.url` → 환경변수에서 읽도록 설정 (alembic/env.py에서 override)

### alembic/env.py
```python
# config.py의 settings.DATABASE_URL 또는 os.environ["DATABASE_URL"]을 읽어
# config.set_main_option("sqlalchemy.url", url) 으로 설정
# target_metadata = Base.metadata (모든 모델 import 후)
```

### 마이그레이션 파일
- 파일명: `0001_initial_schema.py`
- 11개 테이블 전체 CREATE TABLE 포함
- upgrade/downgrade 모두 구현

---

## 실행 명령

```bash
# 마이그레이션 실행
docker compose exec backend alembic upgrade head

# 테이블 확인
docker compose exec postgres psql -U ai_agent -d ai_agent_db -c "\dt"

# 마이그레이션 상태 확인
docker compose exec backend alembic current
```

---

## 완료 조건

```bash
docker compose exec backend alembic upgrade head
# "Running upgrade -> 0001_initial_schema, initial schema" 출력
```

PostgreSQL에 다음 11개 테이블이 생성되어야 한다:

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
alembic_version (자동 생성)
```

---

## 테스트 방법

```bash
# 테이블 목록 확인
docker compose exec postgres psql -U ai_agent -d ai_agent_db -c "\dt"

# 특정 테이블 구조 확인
docker compose exec postgres psql -U ai_agent -d ai_agent_db -c "\d business_concept"

# pgadmin에서 확인
# http://localhost:5050
# Email: admin@example.com / PW: admin
```

---

## Phase 종료 시 생성 문서

Phase 1 완료 후 반드시 다음 문서를 생성/업데이트한다.

### docs/context/COMPACT_READY.md (업데이트)
```markdown
현재 Phase: 1 완료
다음 Phase: 2 (Seed 데이터 구성)
완료 항목: DB 모델 11개, alembic upgrade head 성공
다음 진입 조건: Phase 1 승인 + Seed 데이터 등록 시작
```

### docs/context/CONTEXT_RESTORE.md (업데이트)
Phase 1 완료 결과, 생성된 테이블 목록, Phase 2 작업 내용 업데이트

### docs/phase/PHASE_1_RESULT.md
완료된 파일 목록, alembic 실행 결과, 테이블 생성 확인 내용 기록

---

## 다음 단계 안내

Phase 1 완료 후 사용자 승인을 받은 뒤에만 Phase 2로 진행한다.

**자동으로 Phase 2를 시작하지 않는다.**

Phase 2 시작 조건:
```text
1. alembic upgrade head 성공 확인
2. 11개 테이블 생성 확인
3. 사용자로부터 "Phase 2 시작" 명시적 승인
```

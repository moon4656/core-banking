# PHASE_1_RESULT

Phase: 1 — DB 모델 및 Alembic 마이그레이션
완료일: 2026-06-09

---

## 완료된 작업

- [x] backend/app/core/database.py — SQLAlchemy engine, SessionLocal, Base, get_db
- [x] backend/app/models/__init__.py
- [x] backend/app/models/knowledge_model.py — 7개 테이블
- [x] backend/app/models/agent_model.py — 2개 테이블
- [x] backend/app/models/tool_model.py — placeholder
- [x] backend/app/models/trace_model.py — 2개 테이블
- [x] backend/alembic.ini
- [x] backend/alembic/env.py — DATABASE_URL 환경변수 읽기
- [x] backend/alembic/script.py.mako
- [x] backend/alembic/versions/0001_initial_schema.py — 11개 테이블 CREATE

---

## 생성된 테이블 목록 (11개)

경량 업무 지식 모델:
- business_concept
- business_term_alias
- business_concept_relation
- data_source_catalog
- api_catalog
- concept_data_mapping
- concept_api_mapping
- agent_catalog
- agent_concept_mapping

Trace/Evidence:
- trace_event
- evidence_reference

---

## FK 설계 원칙

- FK 참조 대상: 정수 PK가 아닌 **문자열 business_id** (concept_id, agent_id, api_id, source_id)
- 이유: Seed 데이터 및 API 라우팅 시 문자열 ID가 직접 사용됨

---

## 완료 조건 확인

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -c "
from app.core.database import engine
from sqlalchemy import inspect
print(sorted(inspect(engine).get_table_names()))
"
```

예상 출력:
```
['agent_catalog', 'agent_concept_mapping', 'api_catalog', 'business_concept',
 'business_concept_relation', 'business_term_alias', 'concept_api_mapping',
 'concept_data_mapping', 'data_source_catalog', 'evidence_reference', 'trace_event']
```

---

## 다음 Phase

Phase 2: Seed 데이터

시작 조건:
1. alembic upgrade head 정상 완료
2. 11개 테이블 존재 확인
3. 사용자 "Phase 2 시작" 명시적 승인

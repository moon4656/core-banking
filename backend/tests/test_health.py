# test_health.py — 서비스 기동 상태 확인 테스트
#
# GET /health 는 컨테이너 오케스트레이션(Docker, K8s)에서
# 서비스가 정상 실행 중인지 확인하는 헬스체크 엔드포인트다.
# DB 연결 없이 빠르게 응답해야 한다.

import sqlalchemy as sa


def test_health_check(client):
    """서비스가 정상 기동 중이면 {"status": "ok"} 를 반환한다."""
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "backend"


def _get_table_names(db) -> set:
    """pg_tables에서 public 스키마 테이블 목록을 조회한다."""
    rows = db.execute(
        sa.text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    ).fetchall()
    return {row[0] for row in rows}


def _get_column_names(db, table: str) -> set:
    """information_schema에서 특정 테이블의 컬럼명을 조회한다."""
    rows = db.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t"
        ),
        {"t": table},
    ).fetchall()
    return {row[0] for row in rows}


def test_phase9_trace_v2_tables_exist(db):
    """
    Phase 9 Migration 0010 — Section 13의 신규 5개 테이블이 DB에 존재해야 한다.
    """
    new_tables = [
        "ai_trace_event",
        "ai_evidence_trace",
        "ai_answer_slot_ranking",
        "ai_validation_trace",
        "ai_memory_save_decision",
    ]
    existing = _get_table_names(db)
    for table in new_tables:
        assert table in existing, (
            f"Phase 9 필수 테이블 미생성: {table} — "
            "alembic upgrade head (0010) 실행 필요"
        )


def test_phase9_ai_trace_event_columns(db):
    """ai_trace_event 테이블의 핵심 컬럼이 모두 존재해야 한다."""
    cols = _get_column_names(db, "ai_trace_event")
    required = {"trace_id", "request_id", "session_id", "final_status", "risk_flags", "created_at"}
    missing = required - cols
    assert not missing, f"ai_trace_event 누락 컬럼: {missing}"


def test_phase9_ai_validation_trace_columns(db):
    """ai_validation_trace 테이블의 핵심 컬럼이 모두 존재해야 한다."""
    cols = _get_column_names(db, "ai_validation_trace")
    required = {"validation_id", "trace_id", "check_name", "passed", "severity"}
    missing = required - cols
    assert not missing, f"ai_validation_trace 누락 컬럼: {missing}"

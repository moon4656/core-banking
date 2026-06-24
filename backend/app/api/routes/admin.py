"""
admin.py — 운영·관리 API

[엔드포인트]
  GET    /api/v1/admin/cache/intent-patterns              캐시 현황 조회
  DELETE /api/v1/admin/cache/intent-patterns              전체 캐시 초기화
  DELETE /api/v1/admin/cache/intent-patterns/{intent}     특정 intent 캐시 초기화
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.rate_agent import _INTENT_PATTERN_CACHE, clear_intent_pattern_cache
from app.agents.leader import clear_focus_keywords_cache
from app.core.database import get_db
from app.core.security import require_admin
from app.models.knowledge_model import IntentTermSynonym

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/cache/intent-patterns")
def get_cache_status(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """현재 메모리에 캐시된 intent 패턴 목록과 DB 등록 용어 수를 반환한다."""
    db_counts = (
        db.query(IntentTermSynonym.intent, IntentTermSynonym.is_active)
        .filter(IntentTermSynonym.is_active == True)
        .all()
    )
    intent_counts: dict[str, int] = {}
    for row in db_counts:
        intent_counts[row.intent] = intent_counts.get(row.intent, 0) + 1

    return {
        "cached_intents": list(_INTENT_PATTERN_CACHE.keys()),
        "db_term_counts": intent_counts,
        "note": "캐시된 패턴은 컨테이너 재시작 또는 DELETE API 호출 전까지 유지됩니다.",
    }


@router.delete("/cache/intent-patterns")
def clear_all_cache(_: str = Depends(require_admin)):
    """모든 intent 패턴 캐시를 초기화한다. 다음 요청 시 DB에서 재로딩된다."""
    removed = clear_intent_pattern_cache()
    clear_focus_keywords_cache()
    return {
        "removed": removed,
        "focus_keywords_cache": "cleared",
        "api_concept_cache": "cleared",
        "message": f"{len(removed)}개 rate intent + API 포커스 키워드 + api→concept 역매핑 캐시가 초기화되었습니다.",
    }


@router.delete("/cache/intent-patterns/{intent}")
def clear_intent_cache(intent: str, _: str = Depends(require_admin)):
    """특정 intent의 패턴 캐시만 초기화한다."""
    removed = clear_intent_pattern_cache(intent.upper())
    if not removed:
        return {"removed": [], "message": f"'{intent}' 캐시가 없거나 이미 비어 있습니다."}
    return {
        "removed": removed,
        "message": f"'{intent}' 캐시가 초기화되었습니다.",
    }

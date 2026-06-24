from sqlalchemy.orm import Session

from app.models.memory_model import LongTermMemory

MAX_LTM_TURNS = 5
MAX_QUESTION_LEN = 300
MAX_ANSWER_LEN = 500


def _normalize_summary_text(value: str, limit: int) -> str:
    compact = " ".join((value or "").split())
    if len(compact) <= limit:
        return compact

    sentence_parts = [part.strip() for part in compact.replace("\n", " ").split(".") if part.strip()]
    if sentence_parts:
        summary = ". ".join(sentence_parts[:2]).strip()
        if summary:
            return summary[:limit]
    return compact[:limit]


def load_long_term_history(
    db: Session,
    session_id: str | None,
    limit: int = MAX_LTM_TURNS,
    user_id: str | None = None,
) -> list[dict]:
    # user_id 기준 우선 — 새 대화를 시작해도 같은 사용자의 이전 이력을 참조한다.
    # user_id 없으면 session_id fallback (미로그인 / 테스트 등).
    if not user_id and not session_id:
        return []
    try:
        q = db.query(LongTermMemory)
        if user_id:
            q = q.filter(LongTermMemory.user_id == user_id)
        else:
            q = q.filter(LongTermMemory.session_id == session_id)
        records = (
            q.order_by(LongTermMemory.turn_index.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "turn_index": record.turn_index,
                "intent": record.intent,
                "concepts": record.detected_concepts or [],
                "keywords": record.keywords or [],
                "question": record.question_summary or "",
                "answer": record.answer_summary or "",
            }
            for record in reversed(records)
        ]
    except Exception:
        return []


def save_long_term_memory(
    db: Session,
    session_id: str | None,
    intent: str,
    detected_concepts: list[str],
    keywords: list[str],
    question: str,
    answer: str,
    user_id: str | None = None,
    question_summary: str | None = None,
    answer_summary: str | None = None,
) -> dict:
    if not session_id:
        return {
            "saved": False,
            "reason": "missing_session_id",
            "turn_index": None,
            "question_summary": "",
            "answer_summary": "",
        }

    question_summary = _normalize_summary_text(question_summary or question, MAX_QUESTION_LEN)
    answer_summary = _normalize_summary_text(answer_summary or answer, MAX_ANSWER_LEN)

    try:
        # turn_index: user_id 있으면 사용자 전체 기준, 없으면 세션 기준
        count_q = db.query(LongTermMemory)
        if user_id:
            count_q = count_q.filter(LongTermMemory.user_id == user_id)
        else:
            count_q = count_q.filter(LongTermMemory.session_id == session_id)
        turn_index = count_q.count()

        record = LongTermMemory(
            session_id=session_id,
            user_id=user_id,
            turn_index=turn_index,
            intent=intent,
            detected_concepts=detected_concepts,
            keywords=keywords,
            question_summary=question_summary,
            answer_summary=answer_summary,
        )
        db.add(record)
        db.commit()
        return {
            "saved": True,
            "turn_index": turn_index,
            "question_summary": question_summary,
            "answer_summary": answer_summary,
        }
    except Exception:
        db.rollback()
        return {
            "saved": False,
            "reason": "db_error",
            "turn_index": None,
            "question_summary": question_summary,
            "answer_summary": answer_summary,
        }

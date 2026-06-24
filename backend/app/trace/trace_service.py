# trace_service.py — TraceEvent / EvidenceReference DB 저장 헬퍼 모음
#
# Planner, Executor, ai_gateway 라우터가 모두 이 모듈을 통해 기록한다.
# 직접 TraceEvent/EvidenceReference 모델을 생성하지 말고 여기 함수를 호출한다.
# → 기록 방식을 바꿀 때 이 파일 한 곳만 수정하면 된다.

import time

from sqlalchemy.orm import Session

from app.models.trace_model import EvidenceReference, TraceEvent


def record_event(
    db: Session,
    request_id: str,
    event_type: str,
    agent_id: str | None = None,
    tool_id: str | None = None,
    input_data: dict | None = None,
    output_data: dict | None = None,
    status: str = "success",
    duration_ms: int | None = None,
) -> TraceEvent:
    """
    처리 단계 이벤트를 TraceEvent 테이블에 기록한다.

    event_type 값은 trace_model.py 상단 주석을 참고한다.
    agent_id, tool_id는 해당 단계에서 사용된 경우에만 전달한다.
    duration_ms는 Timer.elapsed_ms()로 측정한 값을 전달한다.
    """
    event = TraceEvent(
        request_id=request_id,
        event_type=event_type,
        agent_id=agent_id,
        tool_id=tool_id,
        input_data=input_data,
        output_data=output_data,
        status=status,
        duration_ms=duration_ms,
    )
    db.add(event)
    db.commit()
    return event


def record_evidence(
    db: Session,
    request_id: str,
    concept_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    content: dict | list | None = None,
    confidence_score: float = 1.0,
) -> EvidenceReference:
    """
    [DEPRECATED] evidence_service.save_evidence_with_score() 를 사용하세요.

    이 함수는 confidence_score를 항상 1.0으로 고정합니다.
    실제 점수 계산(데이터 품질 + 의도 관련도 + 응답 속도)을 원하면
    app.trace.evidence_service.save_evidence_with_score()를 사용하세요.

    이 함수는 외부에서 executor 없이 직접 evidence를 저장해야 하는 경우의
    하위 호환성을 위해 유지됩니다.
    """
    evidence = EvidenceReference(
        request_id=request_id,
        concept_id=concept_id,
        source_type=source_type,
        source_id=source_id,
        content=content if isinstance(content, dict) else {"data": content},
        confidence_score=confidence_score,
    )
    db.add(evidence)
    db.commit()
    return evidence


def count_events(db: Session, request_id: str) -> int:
    """요청 1건에 대한 TraceEvent 기록 건수를 반환한다."""
    return db.query(TraceEvent).filter(TraceEvent.request_id == request_id).count()


def count_evidence(db: Session, request_id: str) -> int:
    """요청 1건에 대한 EvidenceReference 기록 건수를 반환한다."""
    return db.query(EvidenceReference).filter(EvidenceReference.request_id == request_id).count()


class Timer:
    """
    코드 블록의 처리 시간을 측정하는 간단한 타이머.

    [사용법]
        t = Timer()
        # 측정할 코드 실행
        elapsed = t.elapsed_ms()  # 밀리초 단위 경과 시간

    time.monotonic()을 사용하는 이유:
    time.time()은 시스템 시계 변경(NTP 동기화 등)에 영향을 받지만
    time.monotonic()은 항상 증가하는 단조 시계라 경과 시간 측정에 적합하다.
    """
    def __init__(self):
        self._start = time.monotonic()

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start) * 1000)

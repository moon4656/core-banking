from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class StrategyOutcomeLog(Base):
    """재시도/보강 전략 시도 결과 로그.

    trigger_gate × strategy_name 기준으로 성공률을 집계해
    RetryStrategyService.get_best_strategy() 가 최적 전략을 추천한다.
    """

    __tablename__ = "strategy_outcome_log"
    __table_args__ = {
        "comment": "Retry/보강 전략 시도 로그. trigger_gate×strategy_name 집계로 최선 전략을 학습."
    }

    id            = Column(Integer, primary_key=True, index=True, comment="PK")
    request_id    = Column(String(100), nullable=False, index=True,
                           comment="요청 고유 ID (mon_agent_trace.request_id 논리 참조)")
    trigger_gate  = Column(String(64), nullable=False, index=True,
                           comment="트리거 Gate: tool_empty | tool_error | gate1_warn")
    strategy_name = Column(String(64), nullable=False,
                           comment="적용 전략: remove_params | alt_api | expand_synonyms | rewrite_query")
    api_id        = Column(String(128), nullable=True,
                           comment="대상 API ID (tool retry 시); Gate 1 보강 시 NULL")
    intent        = Column(String(128), nullable=True, comment="요청 의도 레이블 (예: INQUIRY)")
    concept_ids   = Column(JSONB, nullable=True, default=list, comment="관련 Concept ID 목록 JSONB")
    outcome       = Column(String(20), nullable=True,
                           comment="결과: success | failed | no_change (update_outcome 호출 시 채워짐)")
    confidence_after = Column(Float, nullable=True,
                              comment="전략 적용 후 신뢰도 (0.0~1.0)")
    latency_ms    = Column(Integer, nullable=True, comment="전략 실행 소요 시간 (ms)")
    error_detail  = Column(Text, nullable=True, comment="실패 시 오류 메시지")
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False,
                           comment="레코드 생성 일시 (UTC)")

"""strategy_service.py — 재시도 전략 로그 기록 및 최적 전략 추천.

strategy_outcome_log 테이블에 재시도 시도를 기록하고,
trigger_gate × strategy_name 기준 성공률로 최적 전략 순서를 반환한다.
"""

from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.strategy_model import StrategyOutcomeLog

# 이력이 없거나 최소 샘플 미달 시 사용하는 기본 전략 순서
_DEFAULT_STRATEGIES: dict[str, list[str]] = {
    "tool_empty": ["remove_params", "alt_api"],
    "tool_error": ["remove_params", "alt_api"],
    "gate1_warn": ["expand_synonyms", "rewrite_query"],
}

_MIN_SAMPLES = 5  # 통계 신뢰성을 위한 최소 샘플 수


class RetryStrategyService:

    @staticmethod
    def log_attempt(
        db: Session,
        request_id: str,
        trigger_gate: str,
        strategy_name: str,
        api_id: str | None,
        intent: str | None,
        concept_ids: list[str],
    ) -> int:
        """재시도 시작 시 로그 행을 삽입하고 row id를 반환한다.

        db.flush()로 id를 확보한다. commit은 leader.py의 기존 타이밍에 귀속.
        """
        row = StrategyOutcomeLog(
            request_id=request_id,
            trigger_gate=trigger_gate,
            strategy_name=strategy_name,
            api_id=api_id,
            intent=intent,
            concept_ids=concept_ids or [],
            outcome=None,
        )
        db.add(row)
        db.flush()
        return row.id

    @staticmethod
    def update_outcome(
        db: Session,
        log_id: int,
        outcome: str,
        confidence_after: float | None = None,
        latency_ms: int | None = None,
        error_detail: str | None = None,
    ) -> None:
        """재시도 완료 후 결과를 채운다.

        outcome: 'success' | 'failed' | 'no_change'
        """
        row = db.get(StrategyOutcomeLog, log_id)
        if row is None:
            return
        row.outcome          = outcome
        row.confidence_after = confidence_after
        row.latency_ms       = latency_ms
        row.error_detail     = error_detail

    @staticmethod
    def get_best_strategy(
        db: Session,
        trigger_gate: str,
        intent: str | None = None,
        concept_ids: list[str] | None = None,
    ) -> list[str]:
        """과거 로그 기반으로 성공률이 높은 전략 순서를 반환한다.

        최소 샘플(_MIN_SAMPLES) 미달이면 _DEFAULT_STRATEGIES를 반환한다.
        intent 필터는 있을 때만 적용 (없으면 gate 전체 이력 사용).
        """
        q = (
            db.query(
                StrategyOutcomeLog.strategy_name,
                func.count().label("total"),
                func.sum(
                    case((StrategyOutcomeLog.outcome == "success", 1), else_=0)
                ).label("successes"),
            )
            .filter(
                StrategyOutcomeLog.trigger_gate == trigger_gate,
                StrategyOutcomeLog.outcome.isnot(None),
            )
        )
        if intent:
            q = q.filter(StrategyOutcomeLog.intent == intent)

        rows = q.group_by(StrategyOutcomeLog.strategy_name).all()

        qualified = [
            (r.strategy_name, r.successes / r.total)
            for r in rows
            if r.total >= _MIN_SAMPLES
        ]

        if not qualified:
            return _DEFAULT_STRATEGIES.get(trigger_gate, [])

        qualified.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in qualified]

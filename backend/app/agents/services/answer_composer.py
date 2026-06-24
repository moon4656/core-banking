from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.schemas.ai_gateway import StepResult
from app.schemas.decision_trace import AnswerSlot, AnswerSlotRanking, ClassifiedConcepts


class AnswerComposer:
    def __init__(
        self,
        *,
        summarize: Callable[..., Awaitable[str]],
        extract_answer_slots: Callable[[ClassifiedConcepts], list[AnswerSlot]],
    ) -> None:
        self._summarize = summarize
        self._extract_answer_slots = extract_answer_slots

    async def compose(
        self,
        *,
        db,
        request_id: str,
        message: str,
        intent_data: dict,
        classified: ClassifiedConcepts,
        raw_results: list[StepResult],
        history: list[dict],
        ltm_history: list[dict] | None = None,
    ) -> tuple[str, list[StepResult], list[AnswerSlot], list[AnswerSlotRanking]]:
        answer_slots = self._extract_answer_slots(classified)
        slot_rankings: list[AnswerSlotRanking] = []
        answer = await self._summarize(
            message=message,
            intent_data=intent_data,
            history=history,
            ranked_results=raw_results,
            ltm_history=ltm_history,
            db=db,
        )
        return answer, raw_results, answer_slots, slot_rankings


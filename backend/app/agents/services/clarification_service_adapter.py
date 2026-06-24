from __future__ import annotations

from app.agents.clarification_service import ClarificationService


class ClarificationServiceAdapter:
    def load_pending(self, session_id: str | None):
        if not session_id:
            return None
        return ClarificationService.load_pending(session_id)

    def clear_pending(self, session_id: str | None) -> None:
        ClarificationService.clear_pending(session_id)

    def save_pending(self, session_id: str | None, state: dict) -> None:
        ClarificationService.save_pending(session_id, state)

    def extract_slot(self, message: str, slot_def: dict) -> str | None:
        return ClarificationService.extract_slot(message, slot_def)

    def build_question(self, slot_def: dict) -> str:
        return ClarificationService.build_question(slot_def)

    def check_missing_slots(self, message: str, detected_concepts: list[str], intent: str) -> list[dict]:
        return ClarificationService.check_missing_slots(message, detected_concepts, intent)

    def try_resolve(self, *, session_id: str | None, pending: dict | None, message: str) -> tuple[dict | None, str | None]:
        if not session_id or not pending:
            return pending, None

        still_missing = []
        for slot in pending["missing_slots"]:
            if slot["name"] in pending.get("filled_slots", {}):
                continue
            extracted = self.extract_slot(message, slot)
            if extracted:
                pending.setdefault("filled_slots", {})[slot["name"]] = extracted
            else:
                still_missing.append(slot)

        if still_missing:
            pending["missing_slots"] = still_missing
            pending["turns"] = pending.get("turns", 0) + 1
            self.save_pending(session_id, pending)
            return pending, self.build_question(still_missing[0])

        self.clear_pending(session_id)
        return None, None

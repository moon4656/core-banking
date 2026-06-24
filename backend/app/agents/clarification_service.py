"""clarification_service.py — Slot Filling 기반 Clarification Dialog.

필수 파라미터(금액, 통화 등)가 빠진 요청을 감지하고
역질문 → 슬롯 추출 → 재실행 패턴을 지원한다.

Redis 키: session:{session_id}:clarification  (TTL 3600s)
"""

from __future__ import annotations

import json
import re

import redis as redis_lib

from app.core.config import settings

# Redis TTL — memory.py와 동일
_SESSION_TTL = 3600
_MAX_TURNS   = 3


def _redis_client():
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def _pending_key(session_id: str) -> str:
    return f"session:{session_id}:clarification"


# ── 슬롯 정의 ─────────────────────────────────────────────────────────────
#
# concept_id → 필요 슬롯 목록
# 각 슬롯:
#   name         : 슬롯 식별자
#   question     : AI가 물어볼 한국어 질문
#   patterns     : 사용자 답변에서 값을 추출하는 regex 목록
#   intent_filter: (optional) 이 intent에서만 체크 (없으면 모든 intent에서 체크)

_CLARIFICATION_SLOTS: dict[str, list[dict]] = {
    "CONCEPT_CURRENCY_EXCHANGE": [
        # amount 슬롯은 방향에 따라 동적으로 생성 (_direction_aware_slots 참조)
        {
            "name": "amount",
            "question": "얼마를 환전하실 건가요? 예) 100만원, 50달러",
            "patterns": [r"\d[\d,.]*\s*(만원|원|달러|엔|유로|위안)"],
        },
        {
            "name": "currency",
            "question": "어떤 통화로 환전하실 건가요? 예) 달러, 엔화, 유로",
            "patterns": [r"달러|USD|엔화|엔|JPY|유로|EUR|위안|CNY|파운드|GBP"],
        },
    ],
    "CONCEPT_FOREIGN_REMITTANCE": [
        {
            "name": "amount",
            "question": "얼마를 송금하실 건가요? 예) 100만원, 500달러",
            "patterns": [r"\d[\d,.]*\s*(만원|원|달러|USD)"],
        },
    ],
    "CONCEPT_PERSONAL_CREDIT_LOAN": [
        {
            "name": "loan_amount",
            "question": "대출 희망 금액이 얼마인가요? 예) 3천만원, 5000만원",
            "patterns": [r"\d[\d,.]*\s*(만원|원|억)"],
            "intent_filter": ["APPLICATION"],
        },
    ],
    "CONCEPT_LOAN_PRODUCT": [
        {
            "name": "loan_type",
            "question": "어떤 대출 상품을 원하시나요? 예) 신용대출, 주택담보대출, 전세대출",
            "patterns": [r"신용|주택담보|전세|사업자|마이너스"],
            "intent_filter": ["APPLICATION"],
        },
    ],
}


def _forex_direction_slots(message: str) -> list[dict]:
    """환전 방향 키워드를 분석해 적절한 amount 슬롯을 반환한다.

    - "원으로 환전" / "원화로" → 외화→KRW 방향 → 외화 금액 질문
    - 그 외 ("달러 환전", "달러로" 등) → KRW→외화 방향 → 원화 금액 질문
    """
    # 통화 표시 (질문에 사용)
    _CCY_LABEL = {
        "달러": "달러(USD)", "USD": "달러(USD)",
        "엔화": "엔화(JPY)", "엔": "엔화(JPY)", "JPY": "엔화(JPY)",
        "유로": "유로(EUR)", "EUR": "유로(EUR)",
        "위안": "위안(CNY)", "CNY": "위안(CNY)",
    }
    target_label = "외화"
    for kw, label in _CCY_LABEL.items():
        if kw in message:
            target_label = label
            break

    # "원으로", "원화로" 키워드 → 외화→KRW 방향
    wants_krw = bool(re.search(r'원(?:화)?으?로', message))

    if wants_krw:
        return [
            {
                "name": "amount",
                "question": f"{target_label}를 얼마나 환전하실 건가요? 예) 100달러, 500유로",
                "patterns": [r"\d[\d,.]*\s*(달러|USD|엔화|엔|JPY|유로|EUR|위안|CNY)"],
            },
        ]
    else:
        return [
            {
                "name": "amount",
                "question": f"원화로 얼마를 {target_label}로 환전하실 건가요? 예) 100만원, 50만원\n  (달러 금액으로 답하시면 해당 달러를 원화로 환전해 드립니다. 예) 1000달러)",
                # 원화 금액 우선, 외화 금액도 수용 (사용자가 "1000달러"로 답해도 처리)
                "patterns": [
                    r"\d[\d,.]*\s*(만원|억)",
                    r"\d[\d,.]*\s*(달러|USD|엔화|엔|JPY|유로|EUR|위안|CNY)",
                ],
            },
        ]


class ClarificationService:

    @staticmethod
    def check_missing_slots(
        message: str,
        detected_concepts: list[str],
        intent: str,
    ) -> list[dict]:
        """탐지된 concept 중 슬롯이 정의된 것을 순회해 빠진 슬롯 목록을 반환한다.

        핵심 규칙: 슬롯이 정의된 concept 중 하나라도 모든 슬롯이 충족되면
        다른 concept의 슬롯 미충족에 관계없이 clarification을 요청하지 않는다.
        예) "50 유로 환전" → CONCEPT_CURRENCY_EXCHANGE 충족 →
            CONCEPT_FOREIGN_REMITTANCE 미충족이어도 질문 안 함.
        """
        missing_per_concept: dict[str, list[dict]] = {}

        for concept_id in detected_concepts:
            # CONCEPT_CURRENCY_EXCHANGE: 방향별 동적 슬롯 사용
            if concept_id == "CONCEPT_CURRENCY_EXCHANGE":
                slots = _forex_direction_slots(message)
            else:
                slots = _CLARIFICATION_SLOTS.get(concept_id)
            if not slots:
                continue
            missing = []
            for slot in slots:
                intent_filter = slot.get("intent_filter")
                if intent_filter and intent not in intent_filter:
                    continue
                if ClarificationService.extract_slot(message, slot) is None:
                    missing.append(slot)
            if not missing:
                # 이 concept의 슬롯이 모두 충족 → clarification 불필요
                return []
            missing_per_concept[concept_id] = missing

        # 우선순위: 환전 > 대출 > 송금 (더 구체적인 개념 우선)
        _PRIORITY = [
            "CONCEPT_CURRENCY_EXCHANGE",
            "CONCEPT_PERSONAL_CREDIT_LOAN",
            "CONCEPT_LOAN_PRODUCT",
            "CONCEPT_FOREIGN_REMITTANCE",
        ]
        for concept_id in _PRIORITY:
            if concept_id in missing_per_concept:
                return missing_per_concept[concept_id]
        # 우선순위 목록에 없는 concept 처리
        for concept_id in detected_concepts:
            if concept_id in missing_per_concept:
                return missing_per_concept[concept_id]
        return []

    @staticmethod
    def extract_slot(message: str, slot_def: dict) -> str | None:
        """regex patterns로 슬롯 값을 추출한다. 첫 번째 match를 반환."""
        for pattern in slot_def.get("patterns", []):
            m = re.search(pattern, message, re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    @staticmethod
    def build_question(slot_def: dict) -> str:
        """슬롯 정의에서 사용자에게 보여줄 질문 문자열을 반환한다."""
        return slot_def["question"]

    @staticmethod
    def save_pending(session_id: str | None, state: dict) -> None:
        """Redis에 pending 상태를 JSON으로 저장한다."""
        if not session_id:
            return
        try:
            client = _redis_client()
            client.setex(_pending_key(session_id), _SESSION_TTL, json.dumps(state, ensure_ascii=False))
        except Exception:
            pass

    @staticmethod
    def load_pending(session_id: str | None) -> dict | None:
        """Redis에서 pending 상태를 조회한다. 없거나 오류 시 None 반환."""
        if not session_id:
            return None
        try:
            client = _redis_client()
            raw = client.get(_pending_key(session_id))
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

    @staticmethod
    def clear_pending(session_id: str | None) -> None:
        """Redis에서 pending 상태를 삭제한다."""
        if not session_id:
            return
        try:
            client = _redis_client()
            client.delete(_pending_key(session_id))
        except Exception:
            pass

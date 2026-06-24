from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.knowledge.concept_service import detect_concepts_in_message, search_concepts
from app.models.knowledge_model import BusinessConceptRelation, IntentTermSynonym


_PRIMARY_CONCEPT_BY_API: dict[str, str] = {
    "MOCK_PRODUCT_LOOKUP": "CONCEPT_LOAN_PRODUCT",
    "MOCK_RATE_LOOKUP": "CONCEPT_INTEREST_RATE",
    "MOCK_RATE_SIMULATION": "CONCEPT_INTEREST_RATE",
    "MOCK_PERSONALIZED_RATE_LOOKUP": "CONCEPT_INTEREST_RATE",
    "MOCK_POLICY_LOOKUP": "CONCEPT_POLICY",
    "MOCK_DOCUMENT_SEARCH": "CONCEPT_REQUIRED_DOCUMENT",
    "MOCK_ELIGIBILITY_CHECK": "CONCEPT_APPLICATION_CONDITION",
    "MOCK_COUNSELING_HISTORY": "CONCEPT_COUNSELING_HISTORY",
    "MOCK_EXCHANGE_RATE_LOOKUP": "CONCEPT_EXCHANGE_RATE",
    "MOCK_CURRENCY_EXCHANGE_CALC": "CONCEPT_CURRENCY_EXCHANGE",
    "MOCK_FOREIGN_REMITTANCE": "CONCEPT_FOREIGN_REMITTANCE",
    "MOCK_FOREIGN_DEPOSIT_RATE": "CONCEPT_FOREIGN_DEPOSIT",
    "MOCK_NOTIFICATION_RULES": "CONCEPT_NOTIFICATION",
    "MOCK_NOTIFICATION_SEND": "CONCEPT_NOTIFICATION",
}

_DEPOSIT_CUES = [
    "\uC678\uD654\uC608\uAE08",
    "\uC678\uD654 \uC608\uAE08",
    "\uB2EC\uB7EC\uC608\uAE08",
    "\uB2EC\uB7EC \uC608\uAE08",
    "\uC678\uD654\uD1B5\uC7A5",
    "\uB2EC\uB7EC \uD1B5\uC7A5",
    "\uC678\uD654 \uACC4\uC88C",
    "\uC678\uD654\uC801\uAE08",
    "\uC678\uD654 \uC815\uAE30\uC608\uAE08",
    "\uC678\uD654 \uBCF4\uD1B5\uC608\uAE08",
    "\uC678\uD654 \uC608\uCE58",
    "\uD1B5\uC7A5",
]

_EXPLICIT_EXCHANGE_RATE_CUES = [
    "\uD658\uC728",
    "exchange rate",
    "\uAE30\uC900\uD658\uC728",
    "\uB9E4\uB9E4\uAE30\uC900\uC728",
    "\uACE0\uC2DC\uD658\uC728",
    "\uD658\uC2DC\uC138",
]


@dataclass
class ResolvedConcepts:
    detected: list[str]
    all_concepts: list[str]
    detected_set: set[str]


class ConceptResolutionService:
    def __init__(self) -> None:
        self._focus_keywords_cache: dict[str, list[str]] | None = None

    def clear_cache(self) -> None:
        self._focus_keywords_cache = None

    def resolve(self, db: Session, message: str, intent_keywords: list[str]) -> ResolvedConcepts:
        detected: list[str] = []
        detected_set: set[str] = set()

        for concept in detect_concepts_in_message(db, message):
            if concept.concept_id not in detected_set:
                detected.append(concept.concept_id)
                detected_set.add(concept.concept_id)

        # Direct alias detection is the highest-signal path. When we already have
        # explicit matches from the message, keyword search tends to add broad
        # partial matches such as "??" -> "????". Use keyword search only
        # as a fallback when direct detection found nothing.
        if not detected:
            for kw in intent_keywords:
                kw = kw.strip()
                if len(kw) <= 1:
                    continue
                for concept in search_concepts(db, kw):
                    if concept.concept_id not in detected_set:
                        detected.append(concept.concept_id)
                        detected_set.add(concept.concept_id)

        self._load_focus_keywords(db)
        for concept_id in self._detect_concepts_via_synonyms(message):
            if concept_id not in detected_set:
                detected.append(concept_id)
                detected_set.add(concept_id)

        detected = self._normalize_detected_concepts(message, detected)
        all_concepts = self._expand_via_relations(db, detected)
        return ResolvedConcepts(
            detected=detected,
            all_concepts=all_concepts,
            detected_set=set(detected),
        )

    def _load_focus_keywords(self, db: Session) -> dict[str, list[str]]:
        if self._focus_keywords_cache is not None:
            return self._focus_keywords_cache

        rows = db.query(IntentTermSynonym.intent, IntentTermSynonym.term).filter(
            IntentTermSynonym.intent.like("MOCK_%"),
            IntentTermSynonym.is_active == True,
        ).all()

        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row.intent, []).append(row.term)

        self._focus_keywords_cache = result
        return result

    def _detect_concepts_via_synonyms(self, message: str) -> list[str]:
        if not self._focus_keywords_cache:
            return []

        msg_lower = message.lower()
        fallback_concepts: list[str] = []
        seen: set[str] = set()

        for api_id, keywords in self._focus_keywords_cache.items():
            if not any(kw in msg_lower for kw in keywords):
                continue

            concept_id = _PRIMARY_CONCEPT_BY_API.get(api_id)
            if concept_id and concept_id not in seen:
                fallback_concepts.append(concept_id)
                seen.add(concept_id)

        return fallback_concepts

    def _normalize_detected_concepts(self, message: str, detected: list[str]) -> list[str]:
        normalized = list(detected)
        msg_lower = message.lower()

        has_foreign_deposit = "CONCEPT_FOREIGN_DEPOSIT" in normalized
        has_deposit_cue = any(cue.lower() in msg_lower for cue in _DEPOSIT_CUES)
        has_explicit_exchange_rate_cue = any(cue.lower() in msg_lower for cue in _EXPLICIT_EXCHANGE_RATE_CUES)

        if has_foreign_deposit and has_deposit_cue:
            if not has_explicit_exchange_rate_cue:
                normalized = [c for c in normalized if c != "CONCEPT_EXCHANGE_RATE"]

            normalized = [
                c for c in normalized
                if c not in {"CONCEPT_INTEREST_RATE", "CONCEPT_PREFERENTIAL_RATE"}
            ]

        return normalized

    def _expand_via_relations(self, db: Session, concept_ids: list[str]) -> list[str]:
        expanded = list(concept_ids)
        seen = set(concept_ids)

        for concept_id in concept_ids:
            relations = (
                db.query(BusinessConceptRelation)
                .filter(
                    BusinessConceptRelation.source_concept_id == concept_id,
                    BusinessConceptRelation.weight >= 0.7,
                )
                .all()
            )
            for relation in relations:
                if relation.target_concept_id not in seen:
                    expanded.append(relation.target_concept_id)
                    seen.add(relation.target_concept_id)

        return expanded

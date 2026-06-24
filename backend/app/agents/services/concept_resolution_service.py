from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.knowledge.concept_service import detect_concepts_in_message, search_concepts
from app.models.knowledge_model import BusinessConceptRelation, ConceptApiMapping, IntentTermSynonym


@dataclass
class ResolvedConcepts:
    detected: list[str]
    all_concepts: list[str]
    detected_set: set[str]


class ConceptResolutionService:
    def __init__(self) -> None:
        self._focus_keywords_cache: dict[str, list[str]] | None = None
        self._api_concept_cache: dict[str, list[str]] | None = None

    def clear_cache(self) -> None:
        self._focus_keywords_cache = None
        self._api_concept_cache = None

    def resolve(self, db: Session, message: str, intent_keywords: list[str]) -> ResolvedConcepts:
        detected: list[str] = []
        detected_set: set[str] = set()

        for concept in detect_concepts_in_message(db, message):
            if concept.concept_id not in detected_set:
                detected.append(concept.concept_id)
                detected_set.add(concept.concept_id)

        for kw in intent_keywords:
            kw = kw.strip()
            if len(kw) <= 1:
                continue
            for concept in search_concepts(db, kw):
                if concept.concept_id not in detected_set:
                    detected.append(concept.concept_id)
                    detected_set.add(concept.concept_id)

        for concept_id in self._detect_concepts_via_synonyms(message, db):
            if concept_id not in detected_set:
                detected.append(concept_id)
                detected_set.add(concept_id)

        all_concepts = self._expand_via_relations(db, detected)
        return ResolvedConcepts(
            detected=detected,
            all_concepts=all_concepts,
            detected_set=detected_set,
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

    def _load_api_concept_map(self, db: Session) -> dict[str, list[str]]:
        if self._api_concept_cache is not None:
            return self._api_concept_cache

        rows = db.query(ConceptApiMapping.api_id, ConceptApiMapping.concept_id).all()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row.api_id, []).append(row.concept_id)

        self._api_concept_cache = result
        return result

    def _detect_concepts_via_synonyms(self, message: str, db: Session) -> list[str]:
        focus_keywords = self._load_focus_keywords(db)
        api_concept_map = self._load_api_concept_map(db)
        msg_lower = message.lower()

        fallback_concepts: list[str] = []
        seen: set[str] = set()
        for api_id, keywords in focus_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                for concept_id in api_concept_map.get(api_id, []):
                    if concept_id not in seen:
                        fallback_concepts.append(concept_id)
                        seen.add(concept_id)

        return fallback_concepts

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


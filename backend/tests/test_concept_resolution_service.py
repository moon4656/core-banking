from app.agents.services.concept_resolution_service import ConceptResolutionService


def test_usd_query_does_not_expand_to_exchange_or_remittance(db):
    service = ConceptResolutionService()

    resolved = service.resolve(db, "USD", ["USD"])

    assert resolved.detected == ["CONCEPT_EXCHANGE_RATE"]
    assert resolved.all_concepts == ["CONCEPT_EXCHANGE_RATE"]


def test_exchange_rate_keyword_stays_on_exchange_rate(db):
    service = ConceptResolutionService()

    resolved = service.resolve(db, "\uAE30\uC900\uD658\uC728 \uC54C\uB824\uC918", ["\uAE30\uC900\uD658\uC728"])

    assert "CONCEPT_EXCHANGE_RATE" in resolved.detected
    assert "CONCEPT_CURRENCY_EXCHANGE" not in resolved.detected
    assert "CONCEPT_FOREIGN_REMITTANCE" not in resolved.detected


def test_direct_remittance_match_skips_noisy_keyword_search(db):
    service = ConceptResolutionService()

    resolved = service.resolve(db, "\uAD6D\uC81C\uC1A1\uAE08 \uD55C\uB3C4 \uC54C\uB824\uC918", ["\uAD6D\uC81C\uC1A1\uAE08", "\uD55C\uB3C4"])

    assert "CONCEPT_FOREIGN_REMITTANCE" in resolved.detected
    assert "CONCEPT_LOAN_PRODUCT" not in resolved.detected
    assert "CONCEPT_PERSONAL_CREDIT_LOAN" not in resolved.detected
    assert "CONCEPT_APPLICATION_CONDITION" not in resolved.detected


def test_foreign_deposit_context_removes_generic_rate_and_currency_noise(db):
    service = ConceptResolutionService()

    resolved = service.resolve(db, "\uB2EC\uB7EC \uD1B5\uC7A5 \uAE08\uB9AC \uC54C\uB824\uC918", ["\uB2EC\uB7EC", "\uD1B5\uC7A5", "\uAE08\uB9AC"])

    assert resolved.detected == ["CONCEPT_FOREIGN_DEPOSIT"]
    assert resolved.all_concepts == ["CONCEPT_FOREIGN_DEPOSIT"]


def test_spaced_dollar_deposit_phrase_maps_to_foreign_deposit(db):
    service = ConceptResolutionService()

    resolved = service.resolve(db, "\uB2EC\uB7EC \uC608\uAE08 \uAE08\uB9AC \uC5BC\uB9C8\uC57C?", ["\uB2EC\uB7EC \uC608\uAE08", "\uAE08\uB9AC"])

    assert resolved.detected == ["CONCEPT_FOREIGN_DEPOSIT"]
    assert resolved.all_concepts == ["CONCEPT_FOREIGN_DEPOSIT"]

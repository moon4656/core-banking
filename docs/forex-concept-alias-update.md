# Forex Concept/Alias Update Notes

Updated scope:
- Added forex aliases for exchange rate, currency exchange, remittance, and foreign deposit.
- Added matching intent synonyms used by concept fallback detection.
- Narrowed synonym fallback so one API maps to one primary concept.
- Added deposit-context normalization so phrases like `달러 통장 금리` and `달러 예금 금리` resolve to `CONCEPT_FOREIGN_DEPOSIT` only.

Why this changed:
- New forex terms were detectable after seeding, but fallback detection was over-expanding into unrelated forex and loan concepts.
- Common foreign-deposit phrases were colliding with generic `금리` and currency aliases.

Verification:
- Seed rerun completed successfully.
- `tests/test_concept_resolution_service.py` passes.
- `tests/test_forex_notification.py` passes.
- Target chat queries now route `달러 통장 금리` and `달러 예금 금리` to `FOREX_AGENT` with `MOCK_FOREIGN_DEPOSIT_RATE` only.

import argparse

from app.core.database import SessionLocal
from app.services.trace_owner_backfill import backfill_trace_owners


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill ai_decision_trace.owner_name from REQUEST_RECEIVED trace events."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of traces to scan.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = backfill_trace_owners(
            db,
            dry_run=not args.apply,
            limit=args.limit,
        )
        mode = "apply" if args.apply else "dry-run"
        print(
            f"[trace-owner-backfill] mode={mode} scanned={result.scanned} "
            f"updated={result.updated} skipped={result.skipped}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

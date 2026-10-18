"""Apply migrations/*.sql to Tiger Data. Safe to re-run (every statement is idempotent).
Run from backend/:  python scripts/migrate.py
Autocommit is required: continuous aggregates cannot be created inside a transaction."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg  # noqa: E402

from app.config import BACKEND_DIR, get_settings  # noqa: E402


def statements(sql: str) -> list[str]:
    sql = re.sub(r"--[^\n]*", "", sql)  # drop comments
    return [s.strip() for s in re.split(r";\s*\n", sql + "\n") if s.strip()]


def main() -> None:
    url = get_settings().tiger_database_url
    if not url:
        sys.exit("TIGER_DATABASE_URL is empty. Put the Tiger connection string in backend/.env first.")
    with psycopg.connect(url, autocommit=True) as conn:
        for path in sorted((BACKEND_DIR / "migrations").glob("*.sql")):
            print(f"== {path.name}")
            for stmt in statements(path.read_text(encoding="utf-8")):
                head = " ".join(stmt.split())[:80]
                try:
                    conn.execute(stmt)
                    print(f"  ok   {head}")
                except Exception as e:  # noqa: BLE001
                    print(f"  FAIL {head}\n       {type(e).__name__}: {str(e).strip()[:300]}")
                    sys.exit(1)
        from app import store
        from app.providers_data import PROVIDERS

        store.upsert_providers(conn, PROVIDERS)
        print(f"== seeded {len(PROVIDERS)} demo providers")
    print("migrations applied")


if __name__ == "__main__":
    main()

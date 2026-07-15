"""Run all six Wave 1 catalog pulls once, politely (24h freshness gate per endpoint).

Each loader owns its own ledger row; a failure in one source is logged (ingest_run.status =
'error') and does not abort the others (honest failures: ledger the error, keep going).
"""

from __future__ import annotations

import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn
from ingest import loaders


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    conn = get_conn()
    results: dict[str, object] = {}
    try:
        for loader in loaders.ALL_LOADERS:
            name = loader.__name__
            try:
                results[name] = loader(conn)
            except Exception as exc:  # noqa: BLE001 - one bad source must not abort the rest
                results[name] = f"ERROR: {exc}"
                logging.getLogger("ingest_all").error("%s failed: %s", name, exc)
    finally:
        conn.close()
    print("\n=== ingest summary ===")
    for name, outcome in results.items():
        print(f"{name}: {outcome}")


if __name__ == "__main__":
    main()

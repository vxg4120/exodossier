"""GET /api/stats -- graph totals, cross-source conflict counts, and the ingestion ledger.

The graph changes only on the nightly rebuild, while Overview, Conflicts and About each ask for
these numbers on load and the conflict counts are four full-table aggregates — so the response is
memoized for a short TTL and the views share one computation.
"""

import time
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.queries import catalog_stats

router = APIRouter(tags=["stats"])

STATS_TTL_S = 300.0
_cached: tuple[float, dict[str, Any]] | None = None  # (monotonic time computed, response)


@router.get("/stats")
def get_stats(db: Annotated[psycopg.Connection, Depends(get_db)]):
    global _cached
    now = time.monotonic()
    if _cached is not None and now - _cached[0] < STATS_TTL_S:
        return _cached[1]
    stats = catalog_stats(db)
    _cached = (now, stats)
    return stats

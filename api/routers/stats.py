"""GET /api/stats -- graph totals, cross-source conflict counts, and the ingestion ledger.

The graph changes only on the nightly rebuild, while Overview, Conflicts and About each ask for
these numbers on load and the conflict counts are three full-graph aggregates — so the response
is memoised (``api.cache``): warmed at start-up, served from memory, refreshed in the background
once stale, and computed once when several cold requests arrive together.
"""

from contextlib import contextmanager
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends

from api.cache import RefreshingCache
from api.deps import get_db
from api.queries import catalog_stats

router = APIRouter(tags=["stats"])

STATS_TTL_S = 300.0


def _refresh_stats() -> dict[str, Any]:
    with contextmanager(get_db)() as conn:
        return catalog_stats(conn)


stats_cache: RefreshingCache[dict[str, Any]] = RefreshingCache("stats", STATS_TTL_S, _refresh_stats)


@router.get("/stats")
def get_stats(db: Annotated[psycopg.Connection, Depends(get_db)]):
    return stats_cache.get(lambda: catalog_stats(db))

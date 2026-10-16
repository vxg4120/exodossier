"""GET /api/stories -- what changed in the archives lately, for the landing page's story panels.

Every block is a diff between retained raw snapshots (``api.stories``), and those snapshots only
move when the nightly pulls land, so the response is memoised like ``/api/stats``: warmed at
start-up, served from memory, refreshed in the background once stale.
"""

from contextlib import contextmanager
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends

from api.cache import RefreshingCache
from api.deps import get_db
from api.stories import catalog_stories

router = APIRouter(tags=["stories"])

STORIES_TTL_S = 300.0


def _refresh_stories() -> dict[str, Any]:
    with contextmanager(get_db)() as conn:
        return catalog_stories(conn)


stories_cache: RefreshingCache[dict[str, Any]] = RefreshingCache(
    "stories", STORIES_TTL_S, _refresh_stories
)


@router.get("/stories")
def get_stories(db: Annotated[psycopg.Connection, Depends(get_db)]):
    return stories_cache.get(lambda: catalog_stories(db))

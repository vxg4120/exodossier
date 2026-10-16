"""GET /api/conflicts?type=disposition|radius|teff -- the browsable "nobody agrees" corpus.

Paginated (limit/offset + total). Every row deep-links to a target via its candidate_id.

The first disposition page is what the landing view (three dramatic rows) and the Conflicts view
(its first forty) both ask for on load, and building it means computing the whole ``conflicted``
set twice. That one page is memoised (``api.cache``) at its largest allowed size and sliced per
request; every other type, page and offset is computed fresh, as before.
"""

from contextlib import contextmanager
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.cache import RefreshingCache
from api.deps import get_db
from api.queries import CONFLICT_TYPES, list_conflicts

router = APIRouter(tags=["conflicts"])

FIRST_PAGE_TTL_S = 300.0
FIRST_PAGE_ROWS = 200  # the endpoint's own upper bound on ``limit``


def _refresh_first_disposition_page() -> dict[str, Any]:
    with contextmanager(get_db)() as conn:
        return list_conflicts(conn, "disposition", FIRST_PAGE_ROWS, 0)


first_disposition_page: RefreshingCache[dict[str, Any]] = RefreshingCache(
    "conflicts.disposition.first_page", FIRST_PAGE_TTL_S, _refresh_first_disposition_page
)


@router.get("/conflicts/types")
def conflict_types():
    """The conflict axes this catalog surfaces, with their plain-English descriptions."""
    return {
        "types": [
            {"type": k, "label": v["label"], "description": v["description"],
             "unit": v.get("unit")}
            for k, v in CONFLICT_TYPES.items()
        ]
    }


@router.get("/conflicts")
def get_conflicts(
    db: Annotated[psycopg.Connection, Depends(get_db)],
    type: Annotated[str, Query(description="disposition | radius | teff")] = "disposition",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if type not in CONFLICT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown conflict type {type!r}; expected one of {list(CONFLICT_TYPES)}",
        )
    if type == "disposition" and offset == 0:
        page = first_disposition_page.get(
            lambda: list_conflicts(db, "disposition", FIRST_PAGE_ROWS, 0)
        )
        return {**page, "rows": page["rows"][:limit], "limit": limit}
    return list_conflicts(db, type, limit, offset)

"""GET /api/search?q= -- resolve any TIC / TOI / CTOI / KOI / planet-name / host to targets."""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.queries import search_targets

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    db: Annotated[psycopg.Connection, Depends(get_db)],
    q: Annotated[str, Query(description="TIC, TOI, CTOI, KOI, planet name, or host name")] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    results = search_targets(db, q, limit)
    return {"query": q, "count": len(results), "results": results}

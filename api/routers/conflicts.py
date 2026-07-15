"""GET /api/conflicts?type=disposition|radius|teff -- the browsable "nobody agrees" corpus.

Paginated (limit/offset + total). Every row deep-links to a target via its candidate_id.
"""

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_db
from api.queries import CONFLICT_TYPES, list_conflicts

router = APIRouter(tags=["conflicts"])


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
    return list_conflicts(db, type, limit, offset)

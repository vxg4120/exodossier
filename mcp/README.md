# ExoDossier MCP server

An **agent-native, read-only** [Model Context Protocol](https://modelcontextprotocol.io) server over
the ExoDossier identity graph and its cross-source conflict findings. Point an MCP client (Claude
Desktop, an agent framework, etc.) at it and ask questions like *"does anyone disagree about whether
TOI-1836 is a planet?"* — the model gets clean JSON with full provenance.

This is, as far as we could verify, the **first exoplanet MCP server**. It surfaces where the
NASA Exoplanet Archive and ExoFOP disagree about the same star or candidate — with provenance — and
**does not adjudicate or confirm**.

## Tools (all read-only)

| Tool | Arguments | Returns |
| --- | --- | --- |
| `catalog_stats` | – | Graph totals + cross-source conflict counts + ingestion ledger |
| `search_targets` | `query`, `limit=25` | Resolve TIC/TOI/CTOI/KOI/name/host → candidate targets |
| `resolve_target` | `id` | Identity + full crosswalk + who-says-what table + conflict flags |
| `target_conflicts` | `id` | Just the attributes that disagree across sources, with per-source claims |
| `list_conflicts` | `type=disposition\|radius\|teff`, `limit=25`, `offset=0` | A page of the conflict corpus |

`id` accepts a `candidate_id` **or** any identifier (a TOI/CTOI/KOI number, a planet name, a TIC, or
a host name — a host resolves to its first candidate).

Each tool returns a single JSON object. `resolve_target` / `target_conflicts` return
`{"error": "not_found", ...}` for an unresolvable id rather than raising.

## Install & run

The server needs the `mcp` SDK plus the repo's `api`/`common` modules and a reachable `exo`
database (`DATABASE_URL`, default `postgresql://oei:oei@localhost:5433/exo`).

```bash
# from the repo root, using the Python 3.14 venv
.venv/bin/pip install -r requirements-api.txt   # fastapi/uvicorn/httpx + mcp==1.14.1
.venv/bin/python mcp/server.py                  # stdio transport; blocks, serving the client
```

> **Python 3.14 note.** `mcp` is pinned to `1.14.1`: newer releases pull `pyjwt[crypto]` →
> `cryptography`, whose current sdist fails to build on 3.14 (no compatible wheel). 1.14.1 is the
> newest release whose dependency set is wheels-only on 3.14 and still ships the API used here.

> The `mcp/` directory is intentionally **not** a Python package (no `__init__.py`) so it never
> shadows the installed `mcp` SDK; `server.py` appends the repo root to `sys.path` to import
> `api.queries`.

## Client configuration

Claude Desktop / any MCP client that launches a stdio server (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "exodossier": {
      "command": "/absolute/path/to/exodossier/.venv/bin/python",
      "args": ["/absolute/path/to/exodossier/mcp/server.py"],
      "env": { "DATABASE_URL": "postgresql://oei:oei@localhost:5433/exo" }
    }
  }
}
```

## Sample agent session

> **User:** Does anyone disagree about whether TOI-1836 is a planet?

The agent calls `search_targets("TOI-1836")`, sees candidate `TOI-1836 c`, then
`target_conflicts("TOI-1836 c")` and gets back:

```json
{
  "target": "TOI-1836 c",
  "host": "TOI-1836",
  "has_conflict": true,
  "conflict_attributes": ["disposition", "..."],
  "conflicts": [
    {
      "attribute": "disposition",
      "assertions": [
        {"source": "exofop_toi",  "value": "FP", "canonical_disposition": "FALSE_POSITIVE"},
        {"source": "nea_toi",     "value": "FP", "canonical_disposition": "FALSE_POSITIVE"},
        {"source": "pscomppars",  "value": "CONFIRMED", "canonical_disposition": "CONFIRMED"},
        {"source": "ps",          "value": "Published Confirmed", "canonical_disposition": "CONFIRMED"}
      ]
    }
  ]
}
```

> **Agent:** Yes — the archives disagree. ExoFOP and the NASA TOI table both mark TOI-1836 c a
> **false positive**, while the Composite table and a published `ps` row call it **confirmed**.
> ExoDossier surfaces the disagreement with provenance; it does not adjudicate which is right.

Other prompts that work well: *"What are the biggest host-temperature disagreements that could flip
a habitable-zone call?"* (`list_conflicts("teff")`), *"Give me the full provenance for Kepler-1517
b."* (`resolve_target`), *"How many candidates does nobody agree on?"* (`catalog_stats`).

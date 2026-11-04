"""MCP server tests — spawn ``mcp/server.py`` over stdio and exercise every tool.

Confirms the server starts, advertises its five read-only tools, and that each returns clean,
correctly-shaped JSON — including the same known-data spot checks the HTTP API is held to
(TRAPPIST-1 Teff conflict; the dramatic disposition corpus) and the argument validation the
server does itself. Read-only; requires a reachable ``exo`` database and the ``mcp`` SDK
(skipped otherwise).
"""

import json
import sys
from pathlib import Path

import pytest

anyio = pytest.importorskip("anyio")
pytest.importorskip("mcp")

from mcp.client.stdio import stdio_client  # noqa: E402

from mcp import ClientSession, StdioServerParameters  # noqa: E402

_SERVER = Path(__file__).resolve().parent.parent / "mcp" / "server.py"

# The server opens the database on every call, so the module is db-marked; the spot checks on
# the populated catalog carry the graph mark individually, so the tool listing and the error
# paths (not found, bad type, bad limit) still run against an empty, migrated graph.
pytestmark = pytest.mark.db


async def _call(tool: str, args: dict) -> dict:
    """Spawn the server, call one tool, return its parsed JSON payload."""
    params = StdioServerParameters(command=sys.executable, args=[str(_SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            assert result.content, f"{tool} returned no content"
            return json.loads(result.content[0].text)


async def _list_tools() -> set[str]:
    params = StdioServerParameters(command=sys.executable, args=[str(_SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            return {t.name for t in listing.tools}


def test_server_advertises_all_tools():
    tools = anyio.run(_list_tools)
    assert tools == {
        "catalog_stats", "search_targets", "resolve_target",
        "target_conflicts", "list_conflicts",
    }


@pytest.mark.graph
def test_catalog_stats_tool():
    data = anyio.run(_call, "catalog_stats", {})
    assert data["stars"] == 20341
    assert data["conflicts"]["disposition"] == 3274
    assert data["conflicts"]["disposition_dramatic"] == 3
    assert data["conflicts"]["teff"] == 1083


@pytest.mark.graph
def test_search_targets_tool():
    data = anyio.run(_call, "search_targets", {"query": "TRAPPIST-1"})
    assert data["count"] == 7
    assert all(r["host"] == "TRAPPIST-1" for r in data["results"])


@pytest.mark.graph
def test_resolve_target_tool_who_says_what():
    data = anyio.run(_call, "resolve_target", {"id": "Kepler-1517 b"})
    assert data["candidate"]["name"] == "Kepler-1517 b"
    assert data["star"]["name"] == "Kepler-1517"
    assert "disposition" in data["conflict_attributes"]
    assert any(a["attribute"] == "disposition" for a in data["attributes"])


@pytest.mark.graph
def test_target_conflicts_tool_trappist_teff():
    data = anyio.run(_call, "target_conflicts", {"id": "TRAPPIST-1 b"})
    assert data["has_conflict"] is True
    assert "teff_k" in data["conflict_attributes"]
    teff = next(c for c in data["conflicts"] if c["attribute"] == "teff_k")
    values = {float(a["value"]) for a in teff["assertions"]}
    assert max(values) >= 5780 and min(values) <= 2600


def test_target_conflicts_tool_not_found():
    data = anyio.run(_call, "target_conflicts", {"id": "definitely-not-a-target-zzz"})
    assert data.get("error") == "not_found"


@pytest.mark.graph
def test_list_conflicts_tool_disposition_dramatic():
    data = anyio.run(_call, "list_conflicts", {"type": "disposition", "limit": 3})
    assert data["total"] == 3274
    assert {r["target"] for r in data["rows"]} == {"Kepler-1517 b", "Kepler-404 b", "TOI-1836 c"}


def test_list_conflicts_tool_bad_type():
    data = anyio.run(_call, "list_conflicts", {"type": "banana"})
    assert data.get("error") == "bad_type"


@pytest.mark.parametrize(
    ("tool", "args", "name"),
    [
        ("search_targets", {"query": "TRAPPIST-1", "limit": 0}, "limit"),
        ("search_targets", {"query": "TRAPPIST-1", "limit": 201}, "limit"),
        ("list_conflicts", {"type": "disposition", "limit": 0}, "limit"),
        ("list_conflicts", {"type": "disposition", "offset": -1}, "offset"),
        ("list_conflicts", {"type": "disposition", "offset": 1_000_001}, "offset"),
    ],
)
def test_out_of_range_limit_and_offset_are_refused_before_sql(tool, args, name):
    """A limit outside 1..200 or an offset outside 0..1,000,000 comes back as a bad_argument
    payload that names the argument, never as a database error or an unbounded query."""
    data = anyio.run(_call, tool, args)
    assert data.get("error") == "bad_argument"
    assert data["message"].startswith(f"{name}=")

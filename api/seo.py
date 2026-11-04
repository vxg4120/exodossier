"""Per-route document metadata for the SPA shell, served from the same table the client uses.

The server hands out one ``index.html`` for every path, so without this a deep link would carry
the root title and canonical to every crawler and social scraper (none of which run the client's
JavaScript). ``render_head`` rewrites the shell's head for the requested path from
``web/public/seo-routes.json`` (``web/dist/seo-routes.json`` once built), with the same matching
rules as react-router's ``matchPath``: static segments compare case-insensitively, a trailing
slash is optional, and ``:param`` segments capture one path segment. An unmatched path gets the
catch-all entry, a ``noindex`` robots tag, no canonical, and status 404.

Pure: no I/O beyond reading the table once.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
from functools import lru_cache
from typing import Any
from urllib.parse import quote

_WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
_TABLE_PATHS = (_WEB / "dist" / "seo-routes.json", _WEB / "public" / "seo-routes.json")


@lru_cache(maxsize=1)
def load_routes() -> dict[str, Any]:
    """The route table: the built copy if there is one, else the source under web/public."""
    for p in _TABLE_PATHS:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("seo-routes.json not found under web/dist or web/public")


def _compile(pattern: str) -> re.Pattern[str]:
    parts = []
    for seg in pattern.strip("/").split("/"):
        if not seg:
            continue
        if seg.startswith(":"):
            parts.append(f"(?P<{seg[1:]}>[^/]+)")
        else:
            parts.append(re.escape(seg))
    body = "/".join(parts)
    return re.compile(rf"^/{body}/?$" if body else r"^/?$", re.IGNORECASE)


def match(path: str) -> dict[str, Any] | None:
    """The route entry for ``path`` with its ``params`` and ``canonical_path`` filled in, or
    ``None`` when nothing but the catch-all applies."""
    for entry in load_routes()["routes"]:
        pattern = entry["pattern"]
        if pattern == "*":
            continue
        m = _compile(pattern).match(path)
        if m is None:
            continue
        params = m.groupdict()
        # a param goes back out percent-encoded exactly as the client's encodeURIComponent does
        # (it leaves ! * ' ( ) bare besides the unreserved set), so "TOI-1836 b" reads %20 and
        # "Teegarden's Star b" keeps its apostrophe on both sides
        canonical_path = "/".join(
            quote(params[seg[1:]], safe="!*'()") if seg.startswith(":") else seg
            for seg in pattern.strip("/").split("/")
        )
        return {**entry, "params": params, "canonical_path": f"/{canonical_path}"}
    return None


def _catch_all() -> dict[str, Any]:
    table = load_routes()
    for entry in table["routes"]:
        if entry["pattern"] == "*":
            return entry
    return {"pattern": "*", "title": table["site"]["name"], "description": "", "noindex": True}


_TITLE = re.compile(r"<title>.*?</title>", re.S)
_ROBOTS = re.compile(r"\s*<meta\s[^>]*?\bname=\"robots\"[^>]*>", re.S)


def _tag(kind: str, attr: str, key: str) -> re.Pattern[str]:
    return re.compile(rf"<{kind}\b[^>]*?\b{attr}=\"{re.escape(key)}\"[^>]*?>", re.S)


def _set_attr(shell: str, kind: str, attr: str, key: str, target: str, value: str) -> str:
    """Set ``target="value"`` on the single ``<kind attr="key" ...>`` element in the head."""
    esc = html.escape(value, quote=True)

    def rewrite(m: re.Match[str]) -> str:
        tag = m.group(0)
        return re.sub(rf"\b{target}=\"[^\"]*\"", f'{target}="{esc}"', tag, count=1, flags=re.S)

    return _tag(kind, attr, key).sub(rewrite, shell, count=1)


def _drop(shell: str, kind: str, attr: str, key: str) -> str:
    return re.compile(rf"\s*<{kind}\b[^>]*?\b{attr}=\"{re.escape(key)}\"[^>]*?>", re.S).sub(
        "", shell, count=1
    )


def render_head(shell: str, path: str) -> tuple[str, int]:
    """The shell with its head rewritten for ``path``, and the status to serve it with."""
    origin = load_routes()["site"]["origin"].rstrip("/")
    entry = match(path)
    if entry is None:
        entry = {**_catch_all(), "noindex": True}
        status = 404
        canonical = None
    elif entry.get("noindex"):
        # a matched route the table keeps out of the index: served, but with no canonical and
        # the robots tag, as the client does for the same entry
        status = 200
        canonical = None
    else:
        status = 200
        cpath = entry["canonical_path"].rstrip("/")
        canonical = f"{origin}{cpath}" if cpath else f"{origin}/"

    out = _TITLE.sub(f"<title>{html.escape(entry['title'])}</title>", shell, count=1)
    out = _set_attr(out, "meta", "name", "description", "content", entry["description"])
    out = _set_attr(out, "meta", "property", "og:title", "content", entry["title"])
    out = _set_attr(out, "meta", "property", "og:description", "content", entry["description"])
    out = _set_attr(out, "meta", "name", "twitter:title", "content", entry["title"])
    out = _set_attr(out, "meta", "name", "twitter:description", "content", entry["description"])
    out = _ROBOTS.sub("", out)
    if canonical:
        out = _set_attr(out, "link", "rel", "canonical", "href", canonical)
        out = _set_attr(out, "meta", "property", "og:url", "content", canonical)
    else:
        out = _drop(out, "link", "rel", "canonical")
        out = _drop(out, "meta", "property", "og:url")
        out = out.replace(
            "</head>", '  <meta name="robots" content="noindex" data-route-meta="" />\n</head>', 1
        )
    return out, status

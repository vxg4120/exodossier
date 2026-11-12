"""The SPA shell's head is rewritten per route on the server (api/seo.py), so a deep link carries
its own title and canonical to crawlers and an unknown path is a real 404 with noindex.

The unit tests run on a small inline shell and need no build. The TestClient tests need
``web/dist/index.html`` and are skipped without it. No database is involved.
"""

import html
import pathlib
import re
import warnings

warnings.filterwarnings("ignore", message=r"Using `httpx`")

import pytest  # noqa: E402

from api.seo import load_routes, match, render_head  # noqa: E402

pytestmark = pytest.mark.filterwarnings(r"ignore:Using `httpx`")

SHELL = """<!doctype html>
<html><head>
<title>ExoDossier · Exoplanet Conflict Explorer</title>
<meta
  name="description"
  content="root description"
/>
<link rel="canonical" href="https://exo.vibcreates.com/" />
<meta property="og:title" content="root" />
<meta property="og:description" content="root description" />
<meta property="og:url" content="https://exo.vibcreates.com/" />
<meta name="twitter:title" content="root" />
<meta name="twitter:description" content="root description" />
</head><body><div id="root"></div></body></html>"""


def _attr(html: str, tag_match: str, attr: str) -> str | None:
    m = re.search(rf"<[^>]*?{tag_match}[^>]*?>", html, re.S)
    if m is None:
        return None
    v = re.search(rf'\b{attr}="([^"]*)"', m.group(0))
    return v.group(1) if v else None


def _title(html: str) -> str:
    return re.search(r"<title>(.*?)</title>", html, re.S).group(1)


def test_root():
    out, status = render_head(SHELL, "/")
    assert status == 200
    assert _title(out) == "ExoDossier · Exoplanet Conflict Explorer"
    assert _attr(out, 'rel="canonical"', "href") == "https://exo.vibcreates.com/"
    assert _attr(out, 'property="og:url"', "content") == "https://exo.vibcreates.com/"
    assert 'name="robots"' not in out
    # the landing is a story page: its own description from the route table, not the site's line
    desc = html.unescape(_attr(out, 'name="description"', "content"))
    assert desc == match("/")["description"]
    assert desc != load_routes()["site"]["description"]


def test_target_keeps_param_case_and_sets_title():
    out, status = render_head(SHELL, "/target/123")
    assert status == 200
    assert _title(out) == "Target · ExoDossier"
    assert _attr(out, 'rel="canonical"', "href") == "https://exo.vibcreates.com/target/123"
    assert _attr(out, 'property="og:title"', "content") == "Target · ExoDossier"
    assert _attr(out, 'name="twitter:title"', "content") == "Target · ExoDossier"
    assert _attr(out, 'name="description"', "content").startswith("One candidate and its host star")
    assert _attr(out, 'property="og:description"', "content") == _attr(
        out, 'name="description"', "content"
    )
    out, _ = render_head(SHELL, "/target/TOI-1234.01")
    assert _attr(out, 'rel="canonical"', "href") == "https://exo.vibcreates.com/target/TOI-1234.01"


def test_trailing_slash_is_optional_and_stripped():
    out, status = render_head(SHELL, "/conflicts/")
    assert status == 200
    assert _title(out) == "Conflicts · ExoDossier"
    assert _attr(out, 'rel="canonical"', "href") == "https://exo.vibcreates.com/conflicts"


def test_static_segments_match_case_insensitively_and_canonicalize_lowercase():
    out, status = render_head(SHELL, "/LightCurves")
    assert status == 200
    assert _title(out) == "Light curves · ExoDossier"
    assert _attr(out, 'rel="canonical"', "href") == "https://exo.vibcreates.com/lightcurves"
    assert match("/Target/9")["canonical_path"] == "/target/9"


def test_unmatched_is_404_noindex_without_canonical():
    out, status = render_head(SHELL, "/nope/here")
    assert status == 404
    assert _title(out) == "Page not found · ExoDossier"
    assert _attr(out, 'name="robots"', "content") == "noindex"
    assert 'rel="canonical"' not in out
    assert 'property="og:url"' not in out
    assert match("/nope/here") is None
    # end: true means a known prefix with extra segments is still unmatched.
    assert match("/search/extra") is None
    assert match("/target") is None


def test_values_are_html_escaped():
    out, _ = render_head(SHELL, "/conflicts")
    desc = _attr(out, 'name="description"', "content")
    assert "Archive&#x27;s" in desc or "Archive's" in desc
    assert '"' not in desc


_DIST = pathlib.Path(__file__).resolve().parent.parent / "web" / "dist" / "index.html"


@pytest.mark.skipif(not _DIST.exists(), reason="web/dist/index.html absent; build the web first")
def test_served_shell_heads():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    r = client.get("/target/1")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert _title(r.text) == "Target · ExoDossier"
    assert _attr(r.text, 'rel="canonical"', "href") == "https://exo.vibcreates.com/target/1"
    assert 'name="robots"' not in r.text

    r = client.get("/nope")
    assert r.status_code == 404
    assert _title(r.text) == "Page not found · ExoDossier"
    assert _attr(r.text, 'name="robots"', "content") == "noindex"
    assert 'rel="canonical"' not in r.text
    assert 'id="root"' in r.text

    r = client.get("/")
    assert r.status_code == 200
    assert _title(r.text) == "ExoDossier · Exoplanet Conflict Explorer"
    # the root is rendered like any route (not the dist file verbatim): the table's description
    # and no-cache, so a stale shell is never kept past a deploy
    served = html.unescape(_attr(r.text, 'name="description"', "content"))
    assert served == match("/")["description"]
    assert r.headers.get("cache-control") == "no-cache"

    # Unknown API paths keep their JSON 404 rather than the shell.
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


# ---- the prerendered body: crawlers that run no script read the route's heading, description
# and links to every section; React clears it on its first render and the shell hides it while
# script runs (api/seo.py, web/index.html).


def _body(out: str) -> str:
    return out[out.index('<div id="root">'):]


def test_root_body_names_the_page_and_links_every_section_without_a_required_param():
    out, _ = render_head(SHELL, "/")
    body = _body(out)
    assert "<h1>ExoDossier · Exoplanet Conflict Explorer</h1>" in body
    links = re.findall(r'<a href="([^"]+)">', body)
    assert links == ["/", "/search", "/conflicts", "/lightcurves", "/followup", "/about"]


def test_a_deep_route_body_carries_its_own_heading_and_description():
    out, status = render_head(SHELL, "/target/TOI-1836")
    assert status == 200
    assert "<h1>Target</h1>" in _body(out)
    assert html.escape(match("/target/x")["description"], quote=True) in _body(out)


def test_an_unknown_path_body_says_not_found_and_links_home():
    out, status = render_head(SHELL, "/nope")
    assert status == 404
    assert "<h1>Page not found</h1>" in _body(out) and '<a href="/">' in _body(out)


def test_the_body_is_filled_once():
    out, _ = render_head(SHELL, "/conflicts")
    again, _ = render_head(out, "/conflicts")
    assert again.count('<div id="root">') == 1 and again.count('class="prerender"') == 1


def test_the_shell_hides_the_prerendered_body_while_script_runs():
    shell = (pathlib.Path(__file__).resolve().parent.parent / "web" / "index.html").read_text()
    assert re.search(r'classList\.add\("js"\)', shell)
    assert re.search(r"\.js \.prerender\s*\{\s*display:\s*none", shell)

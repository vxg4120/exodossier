import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { Results } from "../views/Search";

const noop = () => {};
// the server router: the example links need a router, and this one has no layout effect to warn about
const render = (el: JSX.Element) => renderToStaticMarkup(<StaticRouter location="/search">{el}</StaticRouter>);

/** The result list's three non-list states. A failed search offers its own Retry: retyping the
    same query does not re-run the hook, so without the button the visitor had no way back. */
describe("Search results", () => {
  it("offers a retry when the search failed", () => {
    const html = render(
      <Results query="TOI" loading={false} error="Failed to fetch" results={[]} onPick={noop} reload={noop} />,
    );
    expect(html).toContain("Signal lost");
    expect(html).toContain(">Retry<");
  });
  it("echoes the query and restores the examples when nothing matches", () => {
    const html = render(
      <Results query="zzzzqqq" loading={false} error={null} results={[]} onPick={noop} reload={noop} />,
    );
    expect(html).toContain("No matches for");
    expect(html).toContain('<q class="state__q">zzzzqqq</q>');
    expect(html).toContain('class="example-list"');
  });
  it("shows the examples alone before anything is typed", () => {
    const html = render(
      <Results query="" loading={false} error={null} results={[]} onPick={noop} reload={noop} />,
    );
    expect(html).toContain("Try an example");
    expect(html).not.toContain("No matches");
  });
});

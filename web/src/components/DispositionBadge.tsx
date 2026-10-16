import type { TfopwgCode } from "../api/types";
import { dispositionMeta } from "../lib/dispositions";
import { tfopwgMeta } from "../lib/stories";

/** A TFOPWG code (PC, CP, FP...) on the canonical scale's glyph and color, labelled in words,
    with the code itself in the tooltip. Also names the two ends of a comparison ("New TOI",
    "Dropped") and a TOI with no verdict yet. */
export function TfopwgBadge({ code }: { code: TfopwgCode }) {
  const meta = tfopwgMeta(code);
  return (
    <span className={`badge badge--disp ${meta.className}`} title={meta.title}>
      <span className="badge__glyph" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

/** Canonical disposition as glyph + label — never color alone (accessibility). */
export function DispositionBadge({ disposition }: { disposition: string | null | undefined }) {
  const meta = dispositionMeta(disposition);
  return (
    <span className={`badge badge--disp ${meta.className}`}>
      <span className="badge__glyph" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

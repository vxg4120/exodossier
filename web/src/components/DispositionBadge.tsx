import { dispositionMeta } from "../lib/dispositions";

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

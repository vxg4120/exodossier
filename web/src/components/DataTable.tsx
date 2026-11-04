import type { ReactNode } from "react";
import { fmtInt } from "../lib/format";

export interface Column<Row> {
  key: string;
  header: string;
  num?: boolean;
  render: (row: Row) => ReactNode;
}

interface DataTableProps<Row> {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string | number;
  onRowClick?: (row: Row) => void;
  /** With onRowClick, which rows actually link; the others render as plain rows (no link
      styling, not focusable, no handler). Every row links when omitted. */
  isLinkable?: (row: Row) => boolean;
  /** Pin the first column while the rest scrolls sideways (phones only, see theme.css). */
  stickyFirst?: boolean;
}

/** Dense hairline table. Numeric columns are right-aligned tabular. When onRowClick is set the
    whole row is a keyboard-reachable deep link. */
export function DataTable<Row>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isLinkable,
  stickyFirst,
}: DataTableProps<Row>) {
  return (
    <div className={`table-wrap${stickyFirst ? " table-wrap--sticky-first" : ""}`}>
      <table className="dtable">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.num ? "is-num" : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const onClick = onRowClick && (isLinkable?.(row) ?? true) ? onRowClick : undefined;
            const clickable = Boolean(onClick);
            return (
              <tr
                key={rowKey(row)}
                className={clickable ? "is-link" : undefined}
                onClick={onClick ? () => onClick(row) : undefined}
                tabIndex={clickable ? 0 : undefined}
                onKeyDown={
                  onClick
                    ? (e) => {
                        // a key on a link or control inside the row is that control's own
                        if (e.target !== e.currentTarget) return;
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onClick(row);
                        }
                      }
                    : undefined
                }
              >
                {columns.map((c) => (
                  <td key={c.key} className={c.num ? "is-num" : undefined}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** A page past the end: the list shrank since it was counted, so there is no range to print
    and nothing further to page to. Shared by the pager and the views' empty-page branch. */
export function pastTheEnd(shown: number, total: number): boolean {
  return shown === 0 && total > 0;
}

/** A right-aligned pager for limit/offset endpoints. At either end the button goes inert with
    aria-disabled, not `disabled`: Chromium blurs a control the moment it is disabled, so the
    Prev just pressed to reach page one (or the Next that lands on the last page) would drop the
    keyboard focus to the body as the page arrives. */
export function Pager({
  offset,
  limit,
  total,
  shown,
  onOffset,
}: {
  offset: number;
  limit: number;
  total: number;
  /** Rows on this page, when known: the range then ends where the page really ends. */
  shown?: number;
  onOffset: (next: number) => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + (shown ?? limit), total);
  const empty = shown !== undefined && pastTheEnd(shown, total);
  const canPrev = offset > 0;
  // nothing lies past a page that is already past the end
  const canNext = offset + limit < total && shown !== 0;
  return (
    <div className="pager">
      {/* a status region: a screen reader hears the new range when a page lands (the dimmed
          reload itself is silent) */}
      <span className="num" role="status">
        {empty
          ? `nothing on this page · ${fmtInt(total)} total`
          : `${fmtInt(from)}–${fmtInt(to)} of ${fmtInt(total)}`}
      </span>
      <span className="pager__spacer" />
      <button
        className="btn"
        aria-disabled={!canPrev || undefined}
        onClick={() => {
          if (canPrev) onOffset(Math.max(0, offset - limit));
        }}
      >
        ‹ Prev
      </button>
      <button
        className="btn"
        aria-disabled={!canNext || undefined}
        onClick={() => {
          if (canNext) onOffset(offset + limit);
        }}
      >
        Next ›
      </button>
    </div>
  );
}

/** Renders a nullable numeric/text cell as em-dash when absent. */
export function Cell({ children }: { children: ReactNode }) {
  if (children === null || children === undefined || children === "") {
    return <span className="dash">—</span>;
  }
  return <>{children}</>;
}

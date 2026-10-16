import type { ReactNode } from "react";
import type { AsyncState } from "../hooks/useApi";

/** Spinner + label. With `rows`, also a shimmering skeleton of that many lines, so the page holds
    roughly the height of what it is waiting for instead of jumping when the data lands. */
export function Loading({ label = "Fetching", rows }: { label?: string; rows?: number }) {
  return (
    <div className="state state--loading" role="status" aria-live="polite">
      <div className="inline">
        <span className="spinner" aria-hidden="true" />
        <span className="state__title">{label}…</span>
      </div>
      {rows ? (
        <div className="skeleton" aria-hidden="true">
          {Array.from({ length: rows }, (_, i) => (
            <span className="skeleton__row" key={i} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** What a visitor reads when a fetch fails. The raw message names API paths and browser
    internals; it stays available in the title for whoever is debugging. */
export function visitorMessage(raw: string): string {
  if (/failed to fetch|networkerror|load failed/i.test(raw)) {
    return "The API did not answer. Check your connection, then retry.";
  }
  if (/^no answer\b.* for \//i.test(raw)) {
    return "The API took too long to answer. Retry in a moment.";
  }
  const status = /^(\d{3})\b.* for \//.exec(raw);
  if (status) {
    const code = Number(status[1]);
    if (code === 404) return "Nothing in the catalog answers to that address.";
    if (code >= 500) return "The API hit an error on its side. Retry in a moment.";
    return `The API turned the request down (status ${code}).`;
  }
  return raw;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const shown = visitorMessage(message);
  return (
    <div className="state state--error" role="alert">
      <span className="state__title">Signal lost</span>
      <span className="state__msg" title={shown === message ? undefined : message}>
        {shown}
      </span>
      {onRetry ? (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, message }: { title: ReactNode; message?: ReactNode }) {
  return (
    <div className="state">
      <span className="state__title">{title}</span>
      {message ? <span className="state__msg">{message}</span> : null}
    </div>
  );
}

/** Render children only once data resolves; otherwise the matching state. Every fetch funnels
    through this so loading/error/empty are uniform across the catalog. */
export function Async<T>({
  state,
  loadingLabel,
  loadingRows,
  children,
}: {
  state: AsyncState<T>;
  loadingLabel?: string;
  /** Skeleton lines to hold the space while loading (see Loading). */
  loadingRows?: number;
  children: (data: T) => ReactNode;
}) {
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (state.loading && state.data === null)
    return <Loading label={loadingLabel} rows={loadingRows} />;
  if (state.data === null) return <EmptyState title="No data" />;
  return <>{children(state.data)}</>;
}

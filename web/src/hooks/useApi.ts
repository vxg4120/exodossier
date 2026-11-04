import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  /** The previous data stays through a reload (the `keep` option): Async then keeps the children
      mounted, dimmed, instead of swapping in the loader. */
  keep?: boolean;
}

/**
 * Run an async loader whenever `deps` change, tracking loading/error/data. Stale responses are
 * dropped (cancel flag) so fast successive queries — e.g. typing in search — never render an
 * out-of-order result. `data` is cleared at the start of each run so a dep change never renders the
 * previous identity's result under the new one while the next loads — unless `keep` is set: a paged
 * list keeps its rows (dimmed by Async) while the next page loads, so its pager stays mounted and
 * keeps focus.
 */
export function useApi<T>(
  loader: () => Promise<T>,
  deps: unknown[],
  opts?: { keep?: boolean },
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const keep = Boolean(opts?.keep);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    if (!keep) setData(null);
    run()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Request failed");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [run, nonce, keep]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, reload, keep };
}

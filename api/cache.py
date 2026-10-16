"""Stale-while-revalidate memo for the few expensive, slowly changing responses.

One mechanism, shared by the congestion panel (``twoskies``), the landing-page stats and the
default disposition-conflicts page. The value is served from memory; past its TTL the stale
value keeps being served while one daemon thread recomputes it on its own connection; concurrent
cold requests wait for a single computation instead of each running the scan. ``warm()`` starts
that first computation at process start so no visitor pays for it. A failed refresh keeps the
previous value in service and is logged.
"""

import logging
import threading
import time
from collections.abc import Callable

log = logging.getLogger("api.cache")


class RefreshingCache[T]:
    """``get(compute)`` returns the memoised value. ``refresh`` computes a fresh one on its own
    resources (a connection it opens itself); it runs on the background thread and at warm-up.
    ``compute`` is the request-path alternative for a cold cache, so the first request can reuse
    its own connection."""

    def __init__(self, name: str, ttl_s: float, refresh: Callable[[], T]):
        self.name = name
        self.ttl_s = ttl_s
        self._refresh = refresh
        self._entry: tuple[float, T] | None = None  # (monotonic time computed, value)
        self.refreshing = False
        self._state = threading.Lock()  # guards _entry and refreshing; never held across a query
        self._cold = threading.Lock()  # single-flight for the first computation

    @property
    def value(self) -> T | None:
        with self._state:
            return None if self._entry is None else self._entry[1]

    def reset(self) -> None:
        with self._state:
            self._entry = None
            self.refreshing = False

    def get(self, compute: Callable[[], T]) -> T:
        with self._state:
            entry = self._entry
            if entry is not None:
                if time.monotonic() - entry[0] >= self.ttl_s and not self.refreshing:
                    self.refreshing = True
                    try:
                        threading.Thread(target=self._refresh_in_background, daemon=True).start()
                    except Exception:
                        # The flag would otherwise stay set with no thread to clear it, and no
                        # later request would ever refresh again.
                        self.refreshing = False
                        log.exception(
                            "%s: could not start the refresh; serving the previous value",
                            self.name,
                        )
                return entry[1]
        return self._compute_cold(compute)

    def warm(self, keep_warm: bool = False) -> threading.Thread:
        """Start the first computation on a daemon thread (process start-up). A request that
        arrives meanwhile waits on the same single-flight lock rather than computing again; a
        failure is logged and the next request computes cold as before.

        With ``keep_warm`` the thread then recomputes every ``ttl_s`` regardless of traffic.
        Without it, staleness has no upper bound on a quiet site: the first visitor after an
        idle stretch is served whatever was last computed, however long ago, and only that
        visit triggers the refresh. The timer bounds it to one TTL past the nightly rebuild."""

        def run() -> None:
            try:
                self._compute_cold(self._refresh)
            except Exception:
                log.exception("%s: warm-up failed; the first request computes it", self.name)
            while keep_warm:
                time.sleep(self.ttl_s)
                with self._state:
                    if self.refreshing:
                        continue
                    self.refreshing = True
                self._refresh_in_background()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

    def _compute_cold(self, compute: Callable[[], T]) -> T:
        with self._cold:
            with self._state:
                if self._entry is not None:
                    return self._entry[1]
            value = compute()
            with self._state:
                self._entry = (time.monotonic(), value)
            return value

    def _refresh_in_background(self) -> None:
        try:
            value = self._refresh()
            with self._state:
                self._entry = (time.monotonic(), value)
        except Exception:
            log.exception("%s: refresh failed; the previous value stays in service", self.name)
        finally:
            with self._state:
                self.refreshing = False

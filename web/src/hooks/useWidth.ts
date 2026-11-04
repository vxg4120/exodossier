import { useLayoutEffect, useRef, useState } from "react";

/** Width of the element, tracked with a ResizeObserver; `fallback` until the first measure. The
    story charts and the congestion heatmap draw at their container's measured pixel width rather
    than scaling a viewBox, so type stays at its token size on a phone instead of shrinking with
    the plot. */
export function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth || fallback);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      if (w > 0) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fallback]);
  return [ref, width] as const;
}

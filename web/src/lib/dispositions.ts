/* Canonical disposition + provenance-source vocabulary. Colors live in theme.css; this maps a
   value to its class + label so a disposition always reads as glyph + text, never color alone. */

export interface DispositionMeta {
  className: string;
  label: string;
}

const DISPOSITIONS: Record<string, DispositionMeta> = {
  CONFIRMED: { className: "disp-confirmed", label: "Confirmed" },
  KNOWN_PLANET: { className: "disp-known", label: "Known planet" },
  CANDIDATE: { className: "disp-candidate", label: "Candidate" },
  AMBIGUOUS: { className: "disp-ambiguous", label: "Ambiguous" },
  FALSE_POSITIVE: { className: "disp-fp", label: "False positive" },
};

export function dispositionMeta(disposition: string | null | undefined): DispositionMeta {
  if (!disposition) return { className: "disp-unknown", label: "—" };
  return (
    DISPOSITIONS[disposition.toUpperCase()] ?? { className: "disp-unknown", label: disposition }
  );
}

/** Provenance source -> left-tick class. exofop_toi/exofop_ctoi share the ExoFOP tick, etc. */
export function sourceClass(source: string): string {
  const s = source.toLowerCase();
  if (s.startsWith("exofop")) return "src-exofop";
  if (s === "nea_toi" || s === "nea") return "src-nea";
  if (s === "pscomppars") return "src-pscomppars";
  if (s === "ps") return "src-ps";
  if (s === "koi") return "src-koi";
  return "src-other";
}

/** Ledger run status -> dot class + display label. Total: never throws on an unexpected value. */
export function runStatusMeta(status: string | null | undefined): { className: string; label: string } {
  const map: Record<string, { className: string; label: string }> = {
    ok: { className: "run-ok", label: "ok" },
    error: { className: "run-err", label: "error" },
    skipped_fresh: { className: "run-skip", label: "skipped_fresh" },
  };
  if (!status) return { className: "run-skip", label: "—" };
  return map[status.toLowerCase()] ?? { className: "run-skip", label: status };
}

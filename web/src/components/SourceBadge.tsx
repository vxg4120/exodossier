import { sourceClass } from "../lib/dispositions";

/** Provenance source (exofop_toi / nea_toi / ps / pscomppars / koi / …) as a small mono badge with
    a low-chroma identity tick on the left edge. */
export function SourceBadge({ source }: { source: string }) {
  return (
    <span className={`badge badge--src ${sourceClass(source)}`} title={`Source: ${source}`}>
      {source}
    </span>
  );
}

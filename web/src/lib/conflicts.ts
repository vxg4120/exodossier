/* Conflict-tab metadata — shared by the Overview cards and the Conflicts browser so labels,
   headlines and stats keys never drift. */

import type { ConflictType, Stats } from "../api/types";

export interface ConflictTab {
  key: ConflictType;
  tabLabel: string;
  cardLabel: string;
  cardSub: string;
  headline: string;
  statsKey: keyof Stats["conflicts"];
}

export const CONFLICT_TABS: ConflictTab[] = [
  {
    key: "disposition",
    tabLabel: "Disposition",
    cardLabel: "Disposition conflicts",
    cardSub: "is it even a planet?",
    statsKey: "disposition",
    headline:
      "Candidates whose canonical disposition disagrees across catalogs. The dramatic kind — one " +
      "archive calls it a FALSE POSITIVE while another says CONFIRMED or KNOWN PLANET — is listed " +
      "first. Disagreements are data, not errors; this surfaces them, it does not adjudicate.",
  },
  {
    key: "radius",
    tabLabel: "Planet radius",
    cardLabel: "Radius conflicts",
    cardSub: "rocky vs sub-Neptune flips",
    statsKey: "radius",
    headline:
      "Same candidate, planet radius disagreeing by more than 10% across sources. Gaia parallax " +
      "revisions propagate into stellar and planet radii — this is where rocky-vs-sub-Neptune " +
      "classification flips. Sorted by the widest disagreement first.",
  },
  {
    key: "teff",
    tabLabel: "Host Teff",
    cardLabel: "Host-temperature conflicts",
    cardSub: "can flip the habitable zone",
    statsKey: "teff",
    headline:
      "Host stars whose effective temperature disagrees by more than 5% across catalogs. Kane 2014: " +
      "a ~5% Teff error shifts the habitable-zone boundary ~10%, so HZ membership can depend on which " +
      "catalog you trust. Each row deep-links to a planet of that host.",
  },
];

export function toConflictTab(raw: string | null): ConflictType {
  if (raw === "radius" || raw === "teff") return raw;
  return "disposition";
}

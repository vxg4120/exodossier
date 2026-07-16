/* =============================================================================
   First-visit guided tour (driver.js — MIT-licensed, ~5kb). A short, jargon-light
   walkthrough of the Overview page: it auto-runs once (gated by a localStorage
   flag) and can be replayed anytime from the "?" button in the top bar.
   The popover is repainted for the terminal palette in theme.css (.exo-tour).
   ============================================================================= */
import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";

const TOUR_FLAG = "exo_tour_done";

const STEPS: DriveStep[] = [
  {
    popover: {
      title: "Welcome to ExoDossier",
      description:
        "It surfaces where the exoplanet archives disagree about the same planet — with provenance for every value. Here's a 20-second tour.",
    },
  },
  {
    element: '[data-tour="stats"]',
    popover: {
      title: "The catalog at a glance",
      description:
        "Candidates, host stars, and how many source assertions back them — plus the count of disposition conflicts, where the archives can't agree on what a planet even is.",
      side: "bottom",
      align: "start",
    },
  },
  {
    element: '[data-tour="dramatic"]',
    popover: {
      title: "The sharpest disagreements",
      description:
        "Planets one catalog confirms and another calls a false positive — the starkest form of “nobody agrees on a planet.” Click one to see who said what.",
      side: "left",
      align: "start",
    },
  },
  {
    element: '[data-tour="nav"]',
    popover: {
      title: "Where to go",
      description:
        "Search finds any star or candidate · Conflicts lists every archive disagreement · Follow-up checks it against tonight's sky.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="followup"]',
    popover: {
      title: "Follow-up",
      description:
        "Confirming a candidate from the ground? Check which satellites cross its line of sight during your observation — before you book the telescope.",
      side: "right",
      align: "center",
    },
  },
  {
    popover: {
      title: "That's the tour",
      description:
        "Everything is read-only and every value is cited to its source. MIT-licensed — contributions welcome. Press the “?” in the top bar to replay this anytime.",
    },
  },
];

/** Build and run the tour. Safe to call repeatedly (each call is a fresh instance). */
export function startTour(): void {
  const d = driver({
    showProgress: true,
    animate: true,
    overlayColor: "#05070a",
    overlayOpacity: 0.72,
    stagePadding: 6,
    stageRadius: 4,
    popoverClass: "exo-tour",
    progressText: "{{current}} / {{total}}",
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    doneBtnText: "Done",
  });
  d.setSteps(STEPS);
  d.drive();
}

/** Poll briefly for an anchor to mount (Overview data is async), then run once. */
function whenReady(selector: string, run: () => void, tries = 20): void {
  if (document.querySelector(selector) || tries <= 0) {
    run();
    return;
  }
  window.setTimeout(() => whenReady(selector, run, tries - 1), 150);
}

/** Auto-start on the first visit only, and only on the Overview landing page. */
export function maybeAutoStartTour(): void {
  try {
    if (localStorage.getItem(TOUR_FLAG)) return;
  } catch {
    return; // storage blocked → don't nag, don't crash
  }
  if (window.location.pathname !== "/") return;
  whenReady('[data-tour="stats"]', () => {
    try {
      localStorage.setItem(TOUR_FLAG, "1");
    } catch {
      /* ignore */
    }
    startTour();
  });
}

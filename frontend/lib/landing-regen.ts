/**
 * Section regeneration — shared by Launch Copy tab and (optionally) EditorLayout.
 * Matches EditorLayout.handleRegenerateSection: generate-with-hint → poll →
 * merge one section → caller PATCHes synced copy+page.
 */

import {
  ApiError,
  generateLandingPage,
  getExperiment,
  getLandingPage,
} from "@/lib/api";
import { resolveLandingPageEditorData } from "@/lib/landing-page-data";
import { buildSyncedCopyPatch } from "@/lib/landing-copy-sync";
import type { CopyJson, LandingPage, PageJson } from "@/lib/types";

export type RegeneratableSectionId =
  | "hero"
  | "problem"
  | "features"
  | "comparison"
  | "proof"
  | "objections"
  | "faq"
  | "cta";

const REGEN_POLL_INTERVAL_MS = 1000;
const REGEN_POLL_MAX_ATTEMPTS = 360;
const REGEN_IDLE_MAX_ATTEMPTS = 360;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function wasGeneratedAfter(
  generatedAt: string | undefined,
  pollStartedAt: number,
): boolean {
  if (!generatedAt) return false;
  const parsed = Date.parse(generatedAt);
  if (Number.isNaN(parsed)) return false;
  return parsed >= pollStartedAt - 2_000;
}

export async function waitForLandingGenerationIdle(
  experimentId: string,
): Promise<void> {
  for (let attempt = 0; attempt < REGEN_IDLE_MAX_ATTEMPTS; attempt += 1) {
    const experiment = await getExperiment(experimentId);
    if (experiment.status !== "LANDING_GENERATING") {
      return;
    }
    await wait(REGEN_POLL_INTERVAL_MS);
  }
  throw new Error(
    "Landing page generation is still running. Wait a moment and try again.",
  );
}

export async function fetchRegeneratedLandingPage(options: {
  experimentId: string;
  expectedHint: string;
  pollStartedAt: number;
  displayName?: string | null;
  section?: RegeneratableSectionId;
  previousSectionJson?: string;
  previousGenerationId?: string | null;
}): Promise<LandingPage> {
  const {
    experimentId,
    expectedHint,
    pollStartedAt,
    displayName,
    section,
    previousSectionJson,
    previousGenerationId,
  } = options;

  for (let attempt = 0; attempt < REGEN_POLL_MAX_ATTEMPTS; attempt += 1) {
    const experiment = await getExperiment(experimentId);
    let lp: LandingPage | null = null;

    try {
      lp = await getLandingPage(experimentId);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        throw err;
      }
    }

    if (lp) {
      const nextHint = lp.page_json?.meta?.regeneration_hint;
      const nextGenerationId = lp.page_json?.meta?.generation_id;
      const generatedAt = lp.page_json?.meta?.generated_at;
      const generatedAfterPoll = wasGeneratedAfter(generatedAt, pollStartedAt);

      if (nextHint === expectedHint) {
        return lp;
      }

      if (section && previousSectionJson != null && generatedAfterPoll) {
        const nextSection = resolveLandingPageEditorData(lp, displayName).copy[
          section
        ];
        if (JSON.stringify(nextSection ?? null) !== previousSectionJson) {
          return lp;
        }
      }

      if (
        generatedAfterPoll &&
        previousGenerationId &&
        nextGenerationId &&
        nextGenerationId !== previousGenerationId
      ) {
        return lp;
      }
    }

    if (
      experiment.status !== "LANDING_GENERATING" &&
      experiment.status !== "LANDING_DRAFT" &&
      experiment.status !== "LANDING_LIVE" &&
      attempt >= 5
    ) {
      throw new Error("Landing page regeneration failed. Please try again.");
    }

    await wait(REGEN_POLL_INTERVAL_MS);
  }

  throw new Error("Regeneration timed out. Please try again.");
}

export type RegenerateSectionResult = {
  copy: CopyJson;
  page: PageJson;
  /** True when the section was still identical after the retry attempt. */
  unchangedAfterRetry: boolean;
};

/**
 * Run section regen (with one retry on identical output), merge into local
 * copy, and sync page_json.sections. Caller persists via patchLandingPage.
 */
export async function regenerateLandingSection(args: {
  experimentId: string;
  templateId: string;
  section: RegeneratableSectionId;
  copy: CopyJson;
  page: PageJson;
  displayName?: string | null;
  pageGoal?: string;
}): Promise<RegenerateSectionResult> {
  const {
    experimentId,
    templateId,
    section,
    copy,
    page,
    displayName,
    pageGoal = "waitlist",
  } = args;

  const regenerateOnce = async (hint: string) => {
    const previousSectionJson = JSON.stringify(copy[section] ?? null);
    const previousGenerationId = page?.meta?.generation_id ?? null;
    await waitForLandingGenerationIdle(experimentId);
    const pollStartedAt = Date.now();
    await generateLandingPage(experimentId, {
      template_id: templateId,
      page_goal: pageGoal,
      regeneration_hint: hint,
    });
    return fetchRegeneratedLandingPage({
      experimentId,
      expectedHint: hint,
      pollStartedAt,
      displayName,
      section,
      previousSectionJson,
      previousGenerationId,
    });
  };

  let regeneratedLandingPage = await regenerateOnce(
    `${section}:${Date.now()}:${crypto.randomUUID()}`,
  );
  let resolvedRegen = resolveLandingPageEditorData(
    regeneratedLandingPage,
    displayName,
  );
  let regeneratedSection = resolvedRegen.copy[section];
  const currentSection = copy[section];

  let unchangedAfterRetry = false;

  if (JSON.stringify(regeneratedSection) === JSON.stringify(currentSection)) {
    regeneratedLandingPage = await regenerateOnce(
      `${section}:${Date.now()}:${crypto.randomUUID()}:retry`,
    );
    resolvedRegen = resolveLandingPageEditorData(
      regeneratedLandingPage,
      displayName,
    );
    regeneratedSection = resolvedRegen.copy[section];
    unchangedAfterRetry =
      JSON.stringify(regeneratedSection) === JSON.stringify(currentSection);
  }

  if (regeneratedSection == null) {
    throw new Error(`Missing regenerated section: ${section}`);
  }

  const nextCopy: CopyJson = {
    ...copy,
    [section]: resolvedRegen.copy[section],
  };
  const patch = buildSyncedCopyPatch(
    nextCopy,
    {
      ...page,
      ...resolvedRegen.page,
      template_id: templateId,
      meta: resolvedRegen.page.meta ?? page.meta,
    },
    templateId,
  );

  return {
    copy: patch.copy_json,
    page: patch.page_json,
    unchangedAfterRetry,
  };
}

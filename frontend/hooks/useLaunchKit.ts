"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  getLaunchKit,
  patchLaunchKit,
  LaunchKitVersionConflict,
  type LaunchKit,
  type LaunchKitPatch,
  type ReadinessItem,
} from "@/lib/api-launch-kit";

export type UseLaunchKit = {
  launchKit: LaunchKit | null;
  version: number | null;
  loading: boolean;
  error: string | null;
  /** True when the kit hasn't been generated yet (GET returned 404). */
  notGenerated: boolean;
  refresh: () => void;
  /**
   * Apply a founder edit. Optimistically updates local state, then PATCHes.
   * On 409: toast via `onConflict`, refetch, and retry once if the remote
   * target still matches the pre-conflict intent (checklist only for
   * re-apply; text/channel always retry once with the same patch).
   */
  patch: (
    update: LaunchKitPatch,
    options?: { fieldKey?: string },
  ) => Promise<void>;
  /** True while a PATCH for this field key is in flight. */
  isSaving: (fieldKey: string) => boolean;
  /**
   * Idempotent auto-tick: checks an item if currently unchecked. Never unchecks.
   *
   * Quirk: if a founder manually unticks an auto-ticked item (e.g. `landing_live`
   * while the page is still live), it will not re-tick until the next call
   * (typically next Kit mount or `isLive` transition). Auto-tick only ever checks.
   */
  checkReadinessItem: (id: string) => Promise<void>;
};

type Options = {
  onConflict?: (message: string) => void;
  onError?: (message: string) => void;
};

function applyOptimistic(kit: LaunchKit, update: LaunchKitPatch): LaunchKit {
  const next: LaunchKit = {
    ...kit,
    share_copy_variants: kit.share_copy_variants.map((v) => ({ ...v })),
    readiness_checklist: kit.readiness_checklist.map((r) => ({ ...r })),
    founder_edited: true,
  };

  if (update.first_channel !== undefined) {
    next.first_channel = update.first_channel;
  }
  if (update.first_channel_rationale !== undefined) {
    next.first_channel_rationale = update.first_channel_rationale;
  }
  if (update.first_cohort_hint !== undefined) {
    next.first_cohort_hint = update.first_cohort_hint;
  }
  if (update.share_copy_variants) {
    for (const item of update.share_copy_variants) {
      if (item.index >= 0 && item.index < next.share_copy_variants.length) {
        next.share_copy_variants[item.index] = {
          ...next.share_copy_variants[item.index],
          text: item.text,
        };
      }
    }
  }
  if (update.readiness_checklist) {
    const byId = new Map(
      next.readiness_checklist.map((r) => [r.id, r] as const),
    );
    for (const item of update.readiness_checklist) {
      const target = byId.get(item.id);
      if (target) {
        target.checked_at = item.checked_at;
      }
    }
  }
  return next;
}

function checklistItemState(
  checklist: ReadinessItem[],
  id: string,
): string | null | undefined {
  return checklist.find((r) => r.id === id)?.checked_at;
}

/**
 * Fetch + mutate the LaunchKit for an experiment.
 *
 * Mirrors the EvidenceStagePanel fetch pattern with optimistic PATCH and
 * CAS refetch-retry (never trusts the 409 body's version — backend returns
 * a string message, not a structured current_version).
 */
export function useLaunchKit(
  experimentId: string,
  options: Options = {},
): UseLaunchKit {
  const { onConflict, onError } = options;
  const [launchKit, setLaunchKit] = useState<LaunchKit | null>(null);
  const [version, setVersion] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notGenerated, setNotGenerated] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [savingKeys, setSavingKeys] = useState<ReadonlySet<string>>(
    () => new Set(),
  );

  // Refs so patch always sees the latest kit/version without re-creating
  // the callback on every optimistic flip.
  const kitRef = useRef(launchKit);
  const versionRef = useRef(version);
  kitRef.current = launchKit;
  versionRef.current = version;

  const onConflictRef = useRef(onConflict);
  const onErrorRef = useRef(onError);
  onConflictRef.current = onConflict;
  onErrorRef.current = onError;

  const refresh = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotGenerated(false);
    (async () => {
      try {
        const envelope = await getLaunchKit(experimentId);
        if (cancelled) return;
        setLaunchKit(envelope.launch_kit);
        setVersion(envelope.version);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setLaunchKit(null);
          setVersion(null);
          setNotGenerated(true);
          setLoading(false);
          return;
        }
        setError("Could not load the launch kit.");
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [experimentId, reloadKey]);

  const markSaving = useCallback((fieldKey: string | undefined, on: boolean) => {
    if (!fieldKey) return;
    setSavingKeys((prev) => {
      const next = new Set(prev);
      if (on) next.add(fieldKey);
      else next.delete(fieldKey);
      return next;
    });
  }, []);

  const sendPatch = useCallback(
    async (
      expectedVersion: number,
      update: LaunchKitPatch,
    ): Promise<{ ok: true; kit: LaunchKit; version: number } | { ok: false }> => {
      try {
        const envelope = await patchLaunchKit(experimentId, {
          version: expectedVersion,
          patch: update,
        });
        return {
          ok: true,
          kit: envelope.launch_kit,
          version: envelope.version,
        };
      } catch (err) {
        if (err instanceof LaunchKitVersionConflict || (err instanceof ApiError && err.status === 409)) {
          return { ok: false };
        }
        throw err;
      }
    },
    [experimentId],
  );

  const refetchEnvelope = useCallback(async () => {
    const envelope = await getLaunchKit(experimentId);
    setLaunchKit(envelope.launch_kit);
    setVersion(envelope.version);
    return envelope;
  }, [experimentId]);

  const patch = useCallback(
    async (update: LaunchKitPatch, options?: { fieldKey?: string }) => {
      const currentKit = kitRef.current;
      const currentVersion = versionRef.current;
      if (!currentKit || currentVersion == null) return;

      const fieldKey = options?.fieldKey;
      const snapshot = currentKit;
      const optimistic = applyOptimistic(currentKit, update);
      setLaunchKit(optimistic);
      markSaving(fieldKey, true);

      try {
        const first = await sendPatch(currentVersion, update);
        if (first.ok) {
          setLaunchKit(first.kit);
          setVersion(first.version);
          return;
        }

        // CAS conflict — LaunchKitVersionConflict.current_version defaults to 0
        // because the 409 body is a message string, not a structured version.
        // Always refetch for the true version, then compare/retry against that.
        onConflictRef.current?.(
          "Someone else edited this kit — refreshing.",
        );
        const refreshed = await refetchEnvelope();

        // Checklist: only re-apply if the remote item's checked state still
        // matches what we started from (user's intent hasn't been mirrored).
        let shouldRetry = true;
        if (update.readiness_checklist?.length) {
          const item = update.readiness_checklist[0];
          const remoteNow = checklistItemState(
            refreshed.launch_kit.readiness_checklist,
            item.id,
          );
          const before = checklistItemState(snapshot.readiness_checklist, item.id);
          // If remote already equals our intended checked_at, skip retry.
          if (remoteNow === item.checked_at) {
            shouldRetry = false;
          } else if (remoteNow !== before) {
            // Someone else changed this item differently — don't overwrite.
            shouldRetry = false;
          }
        }

        if (!shouldRetry) return;

        const second = await sendPatch(refreshed.version, update);
        if (second.ok) {
          setLaunchKit(second.kit);
          setVersion(second.version);
          return;
        }

        // Second conflict — accept server truth from another refetch.
        await refetchEnvelope();
      } catch {
        setLaunchKit(snapshot);
        setVersion(currentVersion);
        onErrorRef.current?.("Could not save your change. Try again.");
      } finally {
        markSaving(fieldKey, false);
      }
    },
    [markSaving, refetchEnvelope, sendPatch],
  );

  const isSaving = useCallback(
    (fieldKey: string) => savingKeys.has(fieldKey),
    [savingKeys],
  );

  const checkReadinessItem = useCallback(
    async (id: string) => {
      const kit = kitRef.current;
      if (!kit) return;
      const item = kit.readiness_checklist.find((r) => r.id === id);
      if (!item || item.checked_at !== null) return;
      await patch(
        {
          readiness_checklist: [
            { id, checked_at: new Date().toISOString() },
          ],
        },
        { fieldKey: `readiness:${id}` },
      );
    },
    [patch],
  );

  return {
    launchKit,
    version,
    loading,
    error,
    notGenerated,
    refresh,
    patch,
    isSaving,
    checkReadinessItem,
  };
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { saveSparkVersion } from "@/lib/experiment-api";
import type { Experiment, ExperimentAttachment, SparkVersion } from "@/lib/types";

function idsEqual(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const id of a) {
    if (!b.has(id)) return false;
  }
  return true;
}

type Options = {
  experiment: Experiment;
  attachments: ExperimentAttachment[];
  attachmentsLoading?: boolean;
  onSaved: (experimentPatch: {
    current_spark_version: number;
    raw_idea: string;
  }) => Promise<void> | void;
};

export function useSparkManualSave({
  experiment,
  attachments,
  attachmentsLoading = false,
  onSaved,
}: Options) {
  const [idea, setIdea] = useState(experiment.raw_idea ?? "");
  const [savedIdea, setSavedIdea] = useState(experiment.raw_idea ?? "");
  const [savedAttachmentIds, setSavedAttachmentIds] = useState(
    () => new Set(attachments.map((a) => a.id)),
  );
  const [saving, setSaving] = useState(false);
  const [attachmentsHydrated, setAttachmentsHydrated] = useState(false);

  useEffect(() => {
    setIdea(experiment.raw_idea ?? "");
    setSavedIdea(experiment.raw_idea ?? "");
  }, [experiment.id, experiment.raw_idea]);

  useEffect(() => {
    setAttachmentsHydrated(false);
  }, [experiment.id]);

  // Capture attachment baseline once the list has finished loading.
  useEffect(() => {
    if (attachmentsLoading || attachmentsHydrated) return;
    setSavedAttachmentIds(new Set(attachments.map((a) => a.id)));
    setAttachmentsHydrated(true);
  }, [attachments, attachmentsLoading, attachmentsHydrated]);

  const currentAttachmentIds = useMemo(
    () => new Set(attachments.map((a) => a.id)),
    [attachments],
  );

  const attachmentsChanged =
    attachmentsHydrated &&
    !idsEqual(currentAttachmentIds, savedAttachmentIds);
  const isDirty = idea !== savedIdea || attachmentsChanged;
  const currentVersion = experiment.current_spark_version ?? 0;
  const nextVersion = currentVersion + 1;

  const handleSave = async () => {
    if (!isDirty || saving) return;
    setSaving(true);
    try {
      const version: SparkVersion = await saveSparkVersion(experiment.id, {
        raw_idea: idea,
      });
      setSavedIdea(idea);
      setSavedAttachmentIds(new Set(currentAttachmentIds));
      await onSaved({
        current_spark_version: version.version_number,
        raw_idea: idea,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCloseAttempt = (onClose: () => void) => {
    if (isDirty) {
      const confirmed = window.confirm(
        "You have unsaved changes in Spark. Close without saving?",
      );
      if (!confirmed) return;
    }
    onClose();
  };

  return {
    idea,
    setIdea,
    saving,
    isDirty,
    currentVersion,
    nextVersion,
    handleSave,
    handleCloseAttempt,
  };
}

"use client";

import { useEffect, useState } from "react";
import { DecisionPanel } from "@/components/insight/DecisionPanel";
import type { FounderDecision } from "@/lib/types";
import { InsightReportViewer } from "@/components/insight/InsightReportViewer";
import { InsightUnlockPrompt } from "@/components/wallet/InsightUnlockPrompt";
import { useInsightPaywallGate } from "@/components/wallet/useInsightPaywallGate";
import { shouldShowInsightUnlockPrompt } from "@/lib/insight-flow";
import { isInsightUnlocked, unlockInsight } from "@/lib/wallet-paywall";
import { LoadingState } from "@/components/ui/LoadingState";

interface InsightStagePanelProps {
  experimentId: string;
  experimentStatus: string;
  onDecision: (decision: FounderDecision) => void;
}

export function InsightStagePanel({
  experimentId,
  experimentStatus,
  onDecision,
}: InsightStagePanelProps) {
  const [insightUnlocked, setInsightUnlocked] = useState(false);
  const { requestInsightUnlock, paywallModal } = useInsightPaywallGate();

  useEffect(() => {
    setInsightUnlocked(isInsightUnlocked(experimentId));
  }, [experimentId]);

  const showPrompt = shouldShowInsightUnlockPrompt(
    experimentStatus,
    insightUnlocked,
  );

  function handleUnlock() {
    requestInsightUnlock(() => {
      unlockInsight(experimentId);
      setInsightUnlocked(true);
    });
  }

  if (experimentStatus === "INSIGHT_GENERATING") {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <LoadingState label="Generating insight report…" />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="space-y-4">
        {showPrompt ? (
          <InsightUnlockPrompt onStart={handleUnlock} />
        ) : (
          <>
            <InsightReportViewer experimentId={experimentId} />
            {(experimentStatus === "INSIGHT_READY" ||
              experimentStatus === "COMPLETED") && (
              <DecisionPanel
                experimentId={experimentId}
                onDecision={onDecision}
              />
            )}
          </>
        )}
      </div>
      {paywallModal}
    </div>
  );
}

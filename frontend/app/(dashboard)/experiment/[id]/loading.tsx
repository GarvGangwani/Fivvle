import { ExperimentLoadingScreen } from "@/components/experiment/ExperimentLoadingScreen";

/** Instant pending UI while `/experiment/[id]` JS + data mount. */
export default function ExperimentDetailLoading() {
  return <ExperimentLoadingScreen />;
}

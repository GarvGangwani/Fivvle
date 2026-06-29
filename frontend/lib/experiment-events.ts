export const EXPERIMENTS_CHANGED_EVENT = "fivvle:experiments-changed";

export function notifyExperimentsChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(EXPERIMENTS_CHANGED_EVENT));
}

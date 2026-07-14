const KEY_PREFIX = "fivvle:exp-name:";

export function cacheExperimentName(id: string, name: string): void {
  if (typeof window === "undefined" || !id || !name.trim()) return;
  try {
    sessionStorage.setItem(`${KEY_PREFIX}${id}`, name.trim());
  } catch {
    // ignore quota / private mode
  }
}

export function peekExperimentName(id: string): string | null {
  if (typeof window === "undefined" || !id) return null;
  try {
    return sessionStorage.getItem(`${KEY_PREFIX}${id}`);
  } catch {
    return null;
  }
}

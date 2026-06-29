export function getExperimentDisplayName(experiment: {
  name?: string | null;
  raw_idea?: string | null;
}): string {
  const trimmedName = experiment.name?.trim();
  if (trimmedName) return trimmedName;

  const raw = experiment.raw_idea?.trim() ?? "";
  if (!raw) return "Untitled project";
  if (raw.length <= 50) return raw;
  return `${raw.slice(0, 50)}…`;
}

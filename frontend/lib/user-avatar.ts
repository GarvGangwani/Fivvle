export function getUserInitial(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName?.trim()) {
    return displayName.trim().charAt(0).toUpperCase();
  }
  if (email) return email.charAt(0).toUpperCase();
  return "U";
}

export function getUserFirstName(
  displayName: string | null | undefined,
  email: string | null | undefined,
  fallback = "Founder",
): string {
  if (displayName?.trim()) {
    const first = displayName.trim().split(/\s+/)[0];
    if (first) return first;
  }
  if (email) {
    const local = email.split("@")[0];
    if (local) return local.charAt(0).toUpperCase() + local.slice(1);
  }
  return fallback;
}

export function getUserDisplayName(
  displayName: string | null | undefined,
  email: string | null | undefined,
): string {
  if (displayName?.trim()) return displayName.trim();
  if (email) {
    const local = email.split("@")[0];
    if (local) return local.charAt(0).toUpperCase() + local.slice(1);
  }
  return "Founder";
}

export function getChatUserLabel(
  user: {
    displayName?: string | null;
    email?: string | null;
  } | null | undefined,
): string {
  return getUserFirstName(user?.displayName, user?.email, "User");
}

export function isSafeAvatarUrl(url: string | null | undefined): url is string {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:";
  } catch {
    return false;
  }
}

import { signOut } from "firebase/auth";
import { getFirebaseAuth } from "./firebase";

let redirecting = false;

function isAuthRoute(): boolean {
  if (typeof window === "undefined") return false;
  const path = window.location.pathname;
  return path === "/login" || path === "/signup";
}

/** Clears Firebase session and sends the user to the login page. */
export async function handleSessionExpired(): Promise<void> {
  if (typeof window === "undefined" || isAuthRoute() || redirecting) {
    return;
  }

  redirecting = true;

  try {
    await signOut(getFirebaseAuth());
  } catch {
    /* proceed to login even if sign-out fails */
  }

  window.location.replace("/login");
}

export function isSessionExpiredRedirecting(): boolean {
  return redirecting;
}

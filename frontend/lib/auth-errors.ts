import { FirebaseError } from "firebase/app";
import { ApiError } from "./api";

const FIREBASE_LOGIN_MESSAGES: Record<string, string> = {
  "auth/wrong-password": "Incorrect password. Please try again.",
  "auth/user-not-found":
    "No account found with this email. Try signing up instead.",
  "auth/invalid-credential":
    "Invalid email or password. Please check and try again.",
  "auth/invalid-login-credentials":
    "Invalid email or password. Please check and try again.",
  "auth/too-many-requests":
    "Too many failed attempts. Please wait a moment before trying again.",
  "auth/invalid-email": "Please enter a valid email address.",
  "auth/network-request-failed":
    "Network error. Check your connection and try again.",
  "auth/operation-not-allowed":
    "Email/password sign-in is disabled for this app. Contact support.",
  "auth/user-disabled": "This account has been disabled.",
};

const FIREBASE_SIGNUP_MESSAGES: Record<string, string> = {
  "auth/email-already-in-use":
    "An account with this email already exists. Try logging in.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/invalid-email": "Please enter a valid email address.",
  "auth/network-request-failed":
    "Network error. Check your connection and try again.",
  "auth/operation-not-allowed":
    "Email/password sign-up is disabled for this app. Contact support.",
};

function apiErrorMessage(err: ApiError, fallback: string): string {
  if (err.status === 0) {
    return "Could not reach the backend API. Make sure it is running on http://localhost:8000 and that you are using an allowed frontend URL (localhost:3000 or :3001).";
  }
  if (err.status === 401) {
    return "Your session could not be verified. Ensure frontend and backend both use the fivvle-dev Firebase project.";
  }
  if (process.env.NODE_ENV === "development") {
    const body = err.body;
    if (typeof body === "object" && body !== null && "detail" in body) {
      return `Server error (${err.status}): ${String((body as { detail: unknown }).detail)}`;
    }
    return `Server error (${err.status}): ${JSON.stringify(body)}`;
  }
  return fallback;
}

const FIREBASE_GOOGLE_MESSAGES: Record<string, string> = {
  "auth/popup-closed-by-user": "Google sign-in was cancelled.",
  "auth/cancelled-popup-request": "Google sign-in was cancelled.",
  "auth/popup-blocked":
    "Your browser blocked the sign-in popup. Allow popups for this site and try again.",
  "auth/internal-error":
    "Google sign-in could not start. Confirm Google is enabled in Firebase Authentication, add this site under Authorized domains, then restart the dev server.",
  "auth/account-exists-with-different-credential":
    "An account already exists with this email using a different sign-in method.",
  "auth/network-request-failed":
    "Network error. Check your connection and try again.",
  "auth/operation-not-allowed":
    "Google sign-in is not enabled for this app. Contact support.",
};

function formatFirebaseError(
  err: FirebaseError,
  messages: Record<string, string>,
  fallback: string,
): string {
  return (
    messages[err.code] ??
    (process.env.NODE_ENV === "development"
      ? `Firebase error (${err.code}): ${err.message}`
      : fallback)
  );
}

export function formatGoogleAuthError(err: unknown): string {
  if (err instanceof FirebaseError) {
    return formatFirebaseError(
      err,
      FIREBASE_GOOGLE_MESSAGES,
      "Google sign-in failed. Please try again.",
    );
  }
  if (err instanceof ApiError) {
    return apiErrorMessage(err, "Google sign-in failed. Please try again.");
  }
  if (process.env.NODE_ENV === "development" && err instanceof Error) {
    return err.message;
  }
  return "Google sign-in failed. Please try again.";
}

export function formatLoginError(err: unknown): string {
  if (err instanceof FirebaseError) {
    return formatFirebaseError(
      err,
      FIREBASE_LOGIN_MESSAGES,
      "Login failed. Please try again.",
    );
  }
  if (err instanceof ApiError) {
    return apiErrorMessage(err, "Login failed. Please try again.");
  }
  if (process.env.NODE_ENV === "development" && err instanceof Error) {
    return err.message;
  }
  return "Login failed. Please try again.";
}

export function formatSignupError(err: unknown): string {
  if (err instanceof FirebaseError) {
    return formatFirebaseError(
      err,
      FIREBASE_SIGNUP_MESSAGES,
      "Sign up failed. Please try again.",
    );
  }
  if (err instanceof ApiError) {
    return apiErrorMessage(err, "Sign up failed. Please try again.");
  }
  if (process.env.NODE_ENV === "development" && err instanceof Error) {
    return err.message;
  }
  return "Sign up failed. Please try again.";
}

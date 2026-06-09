"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { FirebaseError } from "firebase/app";
import { useAuth } from "@/lib/auth-context";

const FIREBASE_ERROR_MESSAGES: Record<string, string> = {
  "auth/wrong-password": "Incorrect password. Please try again.",
  "auth/user-not-found":
    "No account found with this email. Try signing up instead.",
  "auth/invalid-credential":
    "Invalid email or password. Please check and try again.",
  "auth/too-many-requests":
    "Too many failed attempts. Please wait a moment before trying again.",
  "auth/invalid-email": "Please enter a valid email address.",
};

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): string | null {
    if (!email.includes("@")) return "Please enter a valid email address.";
    if (password.length === 0) return "Please enter your password.";
    return null;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      await signIn(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof FirebaseError) {
        setError(
          FIREBASE_ERROR_MESSAGES[err.code] ??
            "Login failed. Please try again.",
        );
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--fv-bg)] px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-[var(--fv-text)]">Welcome back</h1>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            Log in to your Fivvle account.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-[var(--fv-text-soft)]"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className="fv-input mt-1 block w-full px-3 py-2 text-sm placeholder:text-[var(--fv-text-muted)] disabled:opacity-50"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-[var(--fv-text-soft)]"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="fv-input mt-1 block w-full px-3 py-2 text-sm placeholder:text-[var(--fv-text-muted)] disabled:opacity-50"
              placeholder="Your password"
            />
          </div>

          {error && (
            <p role="alert" aria-live="polite" className="fv-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="fv-btn-primary w-full justify-center px-4 py-2.5 text-sm disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-fv-bg border-t-transparent" />
                Logging in…
              </span>
            ) : (
              "Log in"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--fv-text-muted)]">
          Don&apos;t have an account?{" "}
          <a
            href="/signup"
            className="font-medium text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
          >
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}

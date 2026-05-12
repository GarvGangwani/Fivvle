"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { FirebaseError } from "firebase/app";
import { useAuth } from "@/lib/auth-context";

const FIREBASE_ERROR_MESSAGES: Record<string, string> = {
  "auth/email-already-in-use":
    "An account with this email already exists. Try logging in.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/invalid-email": "Please enter a valid email address.",
};

export default function SignupPage() {
  const { signUp } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): string | null {
    if (!email.includes("@")) return "Please enter a valid email address.";
    if (password.length < 8) return "Password must be at least 8 characters.";
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
      await signUp(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof FirebaseError) {
        setError(
          FIREBASE_ERROR_MESSAGES[err.code] ??
            "Sign up failed. Please try again.",
        );
      } else {
        setError("Sign up failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Create account</h1>
          <p className="mt-1 text-sm text-gray-500">
            Start validating your startup idea.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700"
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
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 disabled:opacity-50"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 disabled:opacity-50"
              placeholder="Min. 8 characters"
            />
          </div>

          {error && (
            <p
              role="alert"
              aria-live="polite"
              className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Creating account…
              </span>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{" "}
          <a href="/login" className="font-medium text-gray-900 hover:underline">
            Log in
          </a>
        </p>
      </div>
    </div>
  );
}

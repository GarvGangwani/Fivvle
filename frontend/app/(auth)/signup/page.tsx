"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthDivider } from "@/components/auth/AuthDivider";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { useAuthRedirect } from "@/components/auth/useAuthRedirect";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import { AuthSettingsCorner } from "@/components/settings/AuthSettingsCorner";
import { formatSignupError } from "@/lib/auth-errors";
import { useAuth } from "@/lib/auth-context";

export default function SignupPage() {
  const { signUp } = useAuth();
  const router = useRouter();
  useAuthRedirect();

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
      setError(formatSignupError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[var(--fv-bg)] px-4">
      <AuthSettingsCorner />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(61,89,254,0.15),transparent)]" />

      <div className="fv-fade-up w-full max-w-[400px] rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-8 shadow-[0_24px_48px_rgba(0,0,0,0.18)]">
        <FivvleLogo size={40} className="mx-auto mb-6" />

        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-[var(--fv-text)]">Create account</h1>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            Start validating your startup idea.
          </p>
        </div>

        <div className="space-y-5">
          <GoogleSignInButton
            disabled={loading}
            onError={setError}
          />

          <AuthDivider />

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-[13px] font-medium tracking-wide text-[var(--fv-text-soft)]"
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
                className="fv-input block w-full px-4 py-3 text-[15px] placeholder:text-[var(--fv-text-muted)] disabled:opacity-50"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-[13px] font-medium tracking-wide text-[var(--fv-text-soft)]"
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
                className="fv-input block w-full px-4 py-3 text-[15px] placeholder:text-[var(--fv-text-muted)] disabled:opacity-50"
                placeholder="Min. 8 characters"
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
                  Creating account…
                </span>
              ) : (
                "Create account with email"
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-[var(--fv-text-muted)]">
          Already have an account?{" "}
          <a
            href="/login"
            className="font-medium text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
          >
            Log in
          </a>
        </p>
      </div>
    </div>
  );
}

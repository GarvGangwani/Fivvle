"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { sendPasswordResetEmail } from "firebase/auth";
import { FirebaseError } from "firebase/app";
import { AuthCard } from "@/components/auth/AuthCard";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { getFirebaseAuth } from "@/lib/firebase";

const inputClassName =
  "mt-2 w-full rounded-md border-2 border-border-master bg-surface-card px-4 py-3 font-body-md text-body-md text-ink-primary shadow-brutal-sm transition-shadow focus:border-accent focus:shadow-brutal-primary focus:outline-none disabled:opacity-60";

function formatPasswordResetError(err: unknown): string {
  if (err instanceof FirebaseError) {
    if (err.code === "auth/user-not-found") {
      return "No account found with this email.";
    }
    if (err.code === "auth/invalid-email") {
      return "Please enter a valid email address.";
    }
    if (err.code === "auth/too-many-requests") {
      return "Too many requests. Please wait a moment and try again.";
    }
  }
  return "Could not send reset email. Please try again.";
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sentEmail, setSentEmail] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);
    try {
      const auth = getFirebaseAuth();
      await sendPasswordResetEmail(auth, email);
      setSentEmail(email);
    } catch (err) {
      setError(formatPasswordResetError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <AuthCard>
        {sentEmail ? (
          <>
            <h1 className="font-display text-display-lg uppercase leading-none text-ink-primary">
              CHECK YOUR EMAIL
            </h1>
            <p className="mt-4 font-body-lg text-body-lg text-ink-secondary">
              We sent a reset link to{" "}
              <span className="font-semibold text-ink-primary">{sentEmail}</span>
              . Follow it to set a new password.
            </p>
            <Link
              href="/login"
              className={`${marketingButtonClass} mt-8 inline-flex bg-accent px-8 py-4 text-base font-bold uppercase tracking-wider text-ink-inverse no-underline`}
            >
              Back to login
            </Link>
          </>
        ) : (
          <>
            <h1 className="font-display text-display-lg uppercase leading-none text-ink-primary">
              RESET PASSWORD
            </h1>
            <p className="mt-3 font-body-md text-body-md text-ink-secondary">
              Enter your email. We&apos;ll send a reset link.
            </p>

            <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
              <div>
                <label
                  htmlFor="reset-email"
                  className="font-label-md text-label-md uppercase text-ink-secondary"
                >
                  EMAIL
                </label>
                <input
                  id="reset-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={loading}
                  className={inputClassName}
                />
              </div>

              {error ? (
                <p
                  role="alert"
                  aria-live="polite"
                  className="font-body-md text-body-md text-status-critical"
                >
                  {error}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className={`${marketingButtonClass} w-full py-4 text-base font-bold uppercase tracking-wider disabled:cursor-not-allowed ${
                  loading
                    ? "bg-brutalist-yellow text-ink-primary"
                    : "bg-accent text-ink-inverse"
                }`}
              >
                {loading ? "PROCESSING..." : "SEND RESET LINK"}
              </button>
            </form>

            <p className="mt-8 text-center font-body-md text-body-md text-ink-secondary">
              Remember your password?{" "}
              <Link
                href="/login"
                className="font-semibold text-accent no-underline hover:underline"
              >
                Sign In
              </Link>
            </p>
          </>
        )}
      </AuthCard>
    </AuthLayout>
  );
}

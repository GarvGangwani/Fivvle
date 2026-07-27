"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth/AuthCard";
import { AuthEmailDivider } from "@/components/auth/AuthEmailDivider";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { EmailPasswordForm } from "@/components/auth/EmailPasswordForm";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import {
  useAuthDestination,
  useAuthRedirect,
} from "@/components/auth/useAuthRedirect";

function LoginPageContent() {
  const router = useRouter();
  const destination = useAuthDestination();
  useAuthRedirect();

  const [error, setError] = useState<string | null>(null);
  const [formDisabled, setFormDisabled] = useState(false);

  /** Option 2: push immediately; destination loading.tsx + auth status gate the UI. */
  function handleSuccess() {
    router.push(destination);
  }

  return (
    <AuthLayout>
      <AuthCard>
        <h1 className="font-display text-display-lg uppercase leading-none text-ink-primary">
          LOGIN
        </h1>
        <p className="mt-3 font-body-md text-body-md text-ink-secondary">
          Welcome back. Continue your validations.
        </p>

        <div className="mt-8">
          <GoogleSignInButton
            disabled={formDisabled}
            redirectTo={destination}
            ariaLabel="Sign in with Google"
            onError={setError}
          />

          {error ? (
            <p
              role="alert"
              aria-live="polite"
              className="mt-4 font-body-md text-body-md text-status-critical"
            >
              {error}
            </p>
          ) : null}

          <AuthEmailDivider />

          <EmailPasswordForm
            mode="login"
            disabled={formDisabled}
            onSuccess={() => {
              setFormDisabled(true);
              handleSuccess();
            }}
          />
        </div>

        <p className="mt-8 text-center font-body-md text-body-md text-ink-secondary">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-brand-primary no-underline hover:underline"
          >
            Create Account
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <AuthLayout>
          <AuthCard>
            <p className="font-body-md text-body-md text-ink-secondary">
              Loading…
            </p>
          </AuthCard>
        </AuthLayout>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}

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

function SignupPageContent() {
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
      <AuthCard size="wide">
        <h1 className="font-display text-display-lg uppercase leading-none text-ink-primary">
          CREATE ACCOUNT
        </h1>
        <p className="mt-3 font-body-md text-body-md text-ink-secondary">
          Start validating in under a minute.
        </p>

        <div className="mt-8">
          <GoogleSignInButton
            disabled={formDisabled}
            redirectTo={destination}
            label="CONTINUE WITH GOOGLE"
            ariaLabel="Sign up with Google"
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
            mode="signup"
            disabled={formDisabled}
            onSuccess={() => {
              setFormDisabled(true);
              handleSuccess();
            }}
          />
        </div>

        <p className="mt-8 text-center font-body-md text-body-md text-ink-secondary">
          Already registered?{" "}
          <Link
            href="/login"
            className="font-semibold text-brand-primary no-underline hover:underline"
          >
            Sign In
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  );
}

export default function SignupPage() {
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
      <SignupPageContent />
    </Suspense>
  );
}

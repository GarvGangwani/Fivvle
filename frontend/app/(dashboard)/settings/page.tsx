"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useWallet } from "@/lib/wallet-context";
import { ProfileAvatar } from "@/components/dashboard/ProfileAvatar";
import { SettingsSkeleton } from "@/components/dashboard/skeletons/SettingsSkeleton";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { getFirebaseAuth } from "@/lib/firebase";
import { signOut } from "firebase/auth";

export default function SettingsPage() {
  const { user, loading: authLoading } = useAuth();
  const { balance, loading: walletLoading } = useWallet();

  const displayName = user?.displayName ?? "—";
  const email = user?.email ?? "—";
  const provider = user?.providerData?.[0]?.providerId ?? "password";
  async function handleSignOut() {
    await signOut(getFirebaseAuth());
    window.location.href = "/login";
  }

  if (authLoading) {
    return <SettingsSkeleton />;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-12 px-gutter py-12">
      <div>
        <h1 className="font-display text-display-lg uppercase text-ink-primary">
          SETTINGS
        </h1>
        <p className="mt-2 font-body-lg text-body-lg text-ink-secondary">
          Manage your profile, billing, and preferences.
        </p>
      </div>

      <section
        id="profile"
        className="rounded-md border-2 border-border-master bg-surface-card p-8 shadow-brutal-md"
      >
        <div className="mb-2 font-label-md text-label-md uppercase text-brand-primary">
          PROFILE
        </div>
        <h2 className="mb-6 font-headline text-headline-lg text-ink-primary">
          Your account
        </h2>
        <div className="flex items-center gap-4">
          <ProfileAvatar
            photoURL={user?.photoURL}
            displayName={user?.displayName ?? user?.email}
            size="lg"
          />
          <div>
            <p className="font-headline text-headline-md text-ink-primary">
              {displayName}
            </p>
            <p className="font-body-md text-body-md text-ink-secondary">
              {email}
            </p>
            <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
              Provider: {provider}
            </p>
          </div>
        </div>
        <p className="mt-6 font-body-sm text-body-sm text-ink-tertiary">
          TODO: editable name, photo upload
        </p>
      </section>

      <section
        id="billing"
        className="rounded-md border-2 border-border-master bg-surface-card p-8 shadow-brutal-md"
      >
        <div className="mb-2 font-label-md text-label-md uppercase text-brand-primary">
          BILLING
        </div>
        <h2 className="mb-6 font-headline text-headline-lg text-ink-primary">
          Credits and subscription
        </h2>
        <p className="font-display text-display-lg leading-none text-ink-primary">
          {walletLoading ? "…" : (balance?.credits_balance ?? 237)}
        </p>
        <p className="mt-2 font-label-md text-label-md uppercase text-ink-tertiary">
          Credits remaining
        </p>
        <p className="mt-6 font-body-md text-body-md text-ink-secondary">
          Transaction history and purchase flows are stubbed for now.
        </p>
        <p className="mt-2 font-body-sm text-body-sm text-ink-tertiary">
          TODO: real Razorpay wallet integration
        </p>
      </section>

      <section
        id="preferences"
        className="rounded-md border-2 border-border-master bg-surface-card p-8 shadow-brutal-md"
      >
        <div className="mb-2 font-label-md text-label-md uppercase text-brand-primary">
          PREFERENCES
        </div>
        <h2 className="mb-6 font-headline text-headline-lg text-ink-primary">
          Notifications and defaults
        </h2>
        <p className="font-body-md text-body-md text-ink-secondary">
          TODO: email frequency, default geography, default research depth
        </p>
      </section>

      <section
        id="danger"
        className="rounded-md border-2 border-status-critical bg-surface-card p-8 shadow-brutal-md"
      >
        <div className="mb-2 font-label-md text-label-md uppercase text-status-critical">
          DANGER ZONE
        </div>
        <h2 className="mb-6 font-headline text-headline-lg text-ink-primary">
          Account controls
        </h2>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void handleSignOut()}
            className={`${marketingButtonClass} bg-surface-card px-6 py-3 font-label-md text-label-md uppercase text-ink-primary`}
          >
            Sign out
          </button>
          <button
            type="button"
            disabled
            className={`${marketingButtonClass} bg-surface-card px-6 py-3 font-label-md text-label-md uppercase text-ink-tertiary opacity-60`}
          >
            Delete account (stub)
          </button>
        </div>
      </section>

      <p className="text-center">
        <Link
          href="/"
          className="font-label-md text-label-md uppercase text-brand-primary no-underline hover:underline"
        >
          ← Back to home
        </Link>
      </p>
    </div>
  );
}

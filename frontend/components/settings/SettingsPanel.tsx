"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  ExternalLink,
  LogOut,
  Monitor,
  Moon,
  Sun,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useOptionalAuth } from "@/lib/auth-context";
import { usePreferences, type ThemeMode } from "@/lib/preferences-context";
import { getUserDisplayName } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { WalletTransactionHistory } from "@/components/settings/WalletTransactionHistory";

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
}

const THEME_OPTIONS: {
  value: ThemeMode;
  label: string;
  icon: typeof Sun;
}[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

function SettingsToggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4">
      <span className="min-w-0">
        <span className="block text-sm font-medium text-[var(--fv-text)]">
          {label}
        </span>
        <span className="mt-0.5 block text-xs leading-relaxed text-[var(--fv-text-muted)]">
          {description}
        </span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full border transition-colors ${
          checked
            ? "border-accent bg-accent"
            : "border-[var(--fv-border-strong)] bg-[var(--fv-surface-2)]"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-[var(--fv-on-accent)] shadow transition-transform ${
            checked ? "left-[22px]" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}

export function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const { themeMode, setThemeMode, reducedMotion, setReducedMotion } =
    usePreferences();
  const auth = useOptionalAuth();
  const user = auth?.user ?? null;
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  async function handleLogout() {
    if (!auth) return;
    onClose();
    await auth.logOut();
    router.push("/login");
  }

  if (!open || !mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-[300] flex justify-end">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close settings"
        onClick={onClose}
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-panel-title"
        className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-[var(--fv-border)] bg-[var(--fv-surface)] shadow-[-12px_0_48px_rgba(0,0,0,0.45)]"
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--fv-border)] px-5 py-4">
          <div>
            <h2
              id="settings-panel-title"
              className="text-base font-semibold text-[var(--fv-text)]"
            >
              Settings
            </h2>
            <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
              Personalize your Fivvle workspace
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="fv-icon-btn"
            aria-label="Close settings"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <section className="mb-8">
            <h3 className="fv-panel-label mb-3">Appearance</h3>
            <div className="grid grid-cols-3 gap-2">
              {THEME_OPTIONS.map((option) => {
                const Icon = option.icon;
                const active = themeMode === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setThemeMode(option.value)}
                    className={`flex flex-col items-center gap-2 rounded-xl border px-3 py-3 text-center transition-colors ${
                      active
                        ? "border-accent bg-accent-muted text-accent"
                        : "border-[var(--fv-border)] bg-[var(--fv-surface-2)] text-[var(--fv-text-soft)] hover:border-[var(--fv-border-strong)] hover:text-[var(--fv-text)]"
                    }`}
                    aria-pressed={active}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-xs font-medium">{option.label}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="mb-8">
            <h3 className="fv-panel-label mb-3">Accessibility</h3>
            <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface-2)] p-4">
              <SettingsToggle
                checked={reducedMotion}
                onChange={setReducedMotion}
                label="Reduce motion"
                description="Minimize animations and transitions across the app."
              />
            </div>
          </section>

          {user && (
            <>
              <WalletTransactionHistory />

              <section className="mb-8">
                <h3 className="fv-panel-label mb-3">Account</h3>
                <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface-2)] p-4">
                  <div className="flex items-center gap-3">
                    <UserAvatar
                      displayName={user.displayName}
                      email={user.email}
                      photoUrl={user.photoURL}
                      size="md"
                    />
                    <div className="min-w-0">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
                        Signed in as
                      </p>
                      <p className="mt-1 truncate text-sm font-medium text-[var(--fv-text)]">
                        {getUserDisplayName(user.displayName, user.email)}
                      </p>
                      {user.email && (
                        <p className="mt-0.5 truncate text-xs text-[var(--fv-text-muted)]">
                          {user.email}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleLogout()}
                    className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface)] px-3 py-2.5 text-sm font-medium text-[var(--fv-text-soft)] transition-colors hover:border-[var(--fv-border-strong)] hover:text-[var(--fv-text)]"
                  >
                    <LogOut className="h-4 w-4" />
                    Log out
                  </button>
                </div>
              </section>
            </>
          )}

          <section>
            <h3 className="fv-panel-label mb-3">About</h3>
            <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface-2)] p-4">
              <p className="text-sm font-medium text-[var(--fv-text)]">Fivvle</p>
              <p className="mt-1 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                AI-powered startup idea validation — refine, research, launch,
                and measure real founder signal.
              </p>
              <p className="mt-3 text-[11px] text-[var(--fv-text-dim)]">
                Version 0.1.0
              </p>
              <a
                href="https://fivvle.io"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-accent no-underline hover:underline"
              >
                fivvle.io
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </section>
        </div>
      </aside>
    </div>,
    document.body,
  );
}

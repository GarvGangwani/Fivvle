"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { marketingButtonClass } from "@/components/marketing/marketing-styles";
import { useAuth } from "@/lib/auth-context";
import { formatLoginError, formatSignupError } from "@/lib/auth-errors";

const inputClassName =
  "mt-2 w-full rounded-md border-2 border-border-master bg-surface-card px-4 py-3 font-body-md text-body-md text-ink-primary shadow-brutal-sm transition-shadow focus:border-brand-primary focus:shadow-brutal-primary focus:outline-none disabled:opacity-60";

const labelClassName =
  "font-label-md text-label-md uppercase text-ink-secondary";

type SubmitState = "idle" | "loading" | "success";

type PasswordStrength = {
  level: 0 | 1 | 2 | 3 | 4;
  color: string;
  label: string;
};

function getPasswordStrength(password: string): PasswordStrength {
  if (password.length === 0) {
    return { level: 0, color: "", label: "TOO SHORT" };
  }
  if (password.length < 8) {
    return { level: 1, color: "bg-status-critical", label: "WEAK" };
  }

  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasMixedCase = hasLower && hasUpper;
  const hasNumber = /\d/.test(password);
  const hasSymbol = /[^a-zA-Z0-9]/.test(password);

  if (hasMixedCase && hasNumber && hasSymbol) {
    return { level: 4, color: "bg-status-success", label: "STRONG" };
  }
  if (hasMixedCase || hasNumber) {
    return { level: 3, color: "bg-brutalist-yellow", label: "OKAY" };
  }
  return { level: 2, color: "bg-brutalist-yellow", label: "WEAK" };
}

type EmailPasswordFormProps = {
  mode: "login" | "signup";
  /** Called after AuthProvider status is authenticated — push immediately (Option 2). */
  onSuccess: () => void;
  disabled?: boolean;
};

export function EmailPasswordForm({
  mode,
  onSuccess,
  disabled = false,
}: EmailPasswordFormProps) {
  const { signIn, signUp } = useAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<SubmitState>("idle");

  const isSignup = mode === "signup";
  const passwordStrength = getPasswordStrength(password);
  const passwordValid = password.length >= 8;
  const isBusy = submitState !== "idle" || disabled;

  function validate(): string | null {
    if (isSignup) {
      if (!firstName.trim()) return "Please enter your first name.";
      if (!lastName.trim()) return "Please enter your last name.";
    }
    if (!email.includes("@")) return "Please enter a valid email address.";
    if (mode === "login" && password.length === 0) {
      return "Please enter your password.";
    }
    if (isSignup && !passwordValid) {
      return "Password must be at least 8 characters.";
    }
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitState("loading");

    try {
      // AuthProvider sets status → authenticated before these resolve.
      // Parent pushes immediately; destination loading.tsx + useAuth gate the UI.
      if (mode === "login") {
        await signIn(email, password);
      } else {
        const displayName = `${firstName.trim()} ${lastName.trim()}`.trim();
        await signUp(email, password, displayName);
      }

      setSubmitState("success");
      onSuccess();
    } catch (err) {
      setSubmitState("idle");
      setError(
        mode === "login" ? formatLoginError(err) : formatSignupError(err),
      );
    }
  }

  function submitLabel(): string {
    if (submitState === "loading") return "PROCESSING...";
    if (submitState === "success") return "AUTHORIZED";
    return mode === "login" ? "SIGN IN" : "CREATE ACCOUNT";
  }

  function submitClassName(): string {
    if (submitState === "loading") {
      return "bg-brutalist-yellow text-ink-primary";
    }
    if (submitState === "success") {
      return "bg-status-success text-ink-inverse";
    }
    return "bg-brand-primary text-ink-inverse";
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {isSignup ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="firstName" className={labelClassName}>
              FIRST NAME
            </label>
            <input
              id="firstName"
              type="text"
              autoComplete="given-name"
              required
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              disabled={isBusy}
              className={inputClassName}
            />
          </div>
          <div>
            <label htmlFor="lastName" className={labelClassName}>
              LAST NAME
            </label>
            <input
              id="lastName"
              type="text"
              autoComplete="family-name"
              required
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              disabled={isBusy}
              className={inputClassName}
            />
          </div>
        </div>
      ) : null}

      <div>
        <label htmlFor="email" className={labelClassName}>
          EMAIL
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isBusy}
          className={inputClassName}
        />
      </div>

      <div>
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="password" className={labelClassName}>
            PASSWORD
          </label>
          {mode === "login" ? (
            <Link
              href="/forgot-password"
              className="font-label-md text-label-md uppercase text-brand-primary no-underline hover:underline"
            >
              FORGOT?
            </Link>
          ) : null}
        </div>
        <div className="relative mt-2">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            minLength={isSignup ? 8 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isBusy}
            className={`${inputClassName} mt-0 pr-12`}
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            disabled={isBusy}
            className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center justify-center p-2 text-ink-secondary hover:text-ink-primary disabled:opacity-50"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              {showPassword ? "visibility_off" : "visibility"}
            </span>
          </button>
        </div>
        {isSignup ? (
          <div className="mt-2 space-y-2" aria-live="polite">
            <div className="grid grid-cols-4 gap-1">
              {[0, 1, 2, 3].map((index) => (
                <div
                  key={index}
                  className={`h-2 border border-border-master ${
                    index < passwordStrength.level
                      ? passwordStrength.color
                      : "bg-surface-card"
                  }`}
                />
              ))}
            </div>
            <p className="font-mono text-mono-sm uppercase tracking-wide text-ink-tertiary">
              {passwordStrength.label}
            </p>
          </div>
        ) : null}
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
        disabled={isBusy}
        className={`${marketingButtonClass} w-full py-4 text-base font-bold uppercase tracking-wider disabled:cursor-not-allowed ${submitClassName()}`}
      >
        {submitLabel()}
      </button>
    </form>
  );
}

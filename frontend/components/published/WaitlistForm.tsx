"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { submitWaitlistLead, LANDING_PAGE_SOURCE_PARAM } from "@/lib/published-page";

interface WaitlistFormProps {
  slug: string;
  buttonLabel: string;
  className?: string;
  inputClassName?: string;
  buttonClassName?: string;
  metaClassName?: string;
  /** When true, fine print renders below the form instead of inside it (for pill layouts). */
  metaOutsideForm?: boolean;
  wrapperClassName?: string;
  children?: ReactNode;
}

export function WaitlistForm({
  slug,
  buttonLabel,
  className,
  inputClassName,
  buttonClassName,
  metaClassName,
  metaOutsideForm = true,
  wrapperClassName,
  children,
}: WaitlistFormProps) {
  const searchParams = useSearchParams();
  const sourceTag = searchParams.get(LANDING_PAGE_SOURCE_PARAM);

  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      const res = await submitWaitlistLead(slug, email, sourceTag);
      setStatus("done");
      setMessage(res.message);
      setEmail("");
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  if (status === "done") {
    const doneMessage = (
      <p className={metaClassName} style={{ color: "var(--accent, #6366f1)" }}>
        {message}
      </p>
    );
    return metaOutsideForm ? (
      <div className={wrapperClassName}>{doneMessage}</div>
    ) : (
      doneMessage
    );
  }

  const metaContent =
    status === "error" ? (
      <p className={metaClassName} style={{ color: "#dc2626" }}>
        {message}
      </p>
    ) : (
      <p className={metaClassName}>No spam · Unsubscribe anytime</p>
    );

  const form = (
    <form className={className} onSubmit={onSubmit}>
      {children}
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@company.com"
        className={inputClassName}
        disabled={status === "loading"}
        autoComplete="email"
      />
      <button type="submit" className={buttonClassName} disabled={status === "loading"}>
        {status === "loading" ? "Sending…" : buttonLabel}
      </button>
      {!metaOutsideForm && metaContent}
    </form>
  );

  if (metaOutsideForm) {
    return (
      <div className={wrapperClassName}>
        {form}
        {metaContent}
      </div>
    );
  }

  return form;
}

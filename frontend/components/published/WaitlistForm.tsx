"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { submitWaitlistLead } from "@/lib/published-page";

interface WaitlistFormProps {
  slug: string;
  buttonLabel: string;
  className?: string;
  inputClassName?: string;
  buttonClassName?: string;
  metaClassName?: string;
  children?: ReactNode;
}

export function WaitlistForm({
  slug,
  buttonLabel,
  className,
  inputClassName,
  buttonClassName,
  metaClassName,
  children,
}: WaitlistFormProps) {
  const searchParams = useSearchParams();
  const sourceTag = searchParams.get("ref");

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
    return (
      <p className={metaClassName} style={{ color: "var(--accent, #6366f1)" }}>
        {message}
      </p>
    );
  }

  return (
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
      />
      <button type="submit" className={buttonClassName} disabled={status === "loading"}>
        {status === "loading" ? "Sending…" : buttonLabel}
      </button>
      {status === "error" && (
        <p className={metaClassName} style={{ color: "var(--fv-danger)" }}>
          {message}
        </p>
      )}
      {status !== "error" && (
        <p className={metaClassName}>No spam · Unsubscribe anytime</p>
      )}
    </form>
  );
}

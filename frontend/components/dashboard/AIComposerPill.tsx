"use client";

import { FormEvent, useEffect, useState } from "react";
import { useComposerFocus } from "./composer-focus-context";

export function AIComposerPill() {
  const { inputRef } = useComposerFocus();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [inputRef]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = message.trim();
    if (!value || submitting) return;

    setSubmitting(true);
    try {
      const response = await fetch("/api/composer/stub", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: value }),
      });
      const data = (await response.json().catch(() => ({}))) as {
        echo?: string;
      };
      const echoed = data.echo ?? value;
      setToast(
        `Composer real implementation pending — tracked-work #8. Your message was: ${echoed}`,
      );
      setMessage("");
    } catch {
      setToast("Composer stub unavailable. Try again later.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="fixed bottom-8 left-1/2 z-50 hidden w-full max-w-2xl -translate-x-1/2 items-center gap-2 rounded-full border-2 border-brand-primary bg-surface-card p-2 shadow-brutal-md md:flex"
      >
        <span
          className="material-symbols-outlined pl-3 text-brand-primary"
          aria-hidden
        >
          auto_awesome
        </span>
        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask Fivvle to do anything..."
          aria-label="Ask Fivvle to do anything"
          className="min-w-0 flex-1 border-0 bg-transparent font-body-md text-body-md text-ink-primary placeholder:text-ink-tertiary focus:outline-none focus:ring-0"
          disabled={submitting}
        />
        <button
          type="submit"
          disabled={submitting || !message.trim()}
          className="shrink-0 rounded-full bg-brand-primary px-6 py-3 font-label-md text-label-md uppercase text-ink-inverse disabled:opacity-60"
        >
          {submitting ? "PROCESSING..." : "COMPOSE"}
        </button>
      </form>

      {toast ? (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-28 left-1/2 z-50 hidden max-w-xl -translate-x-1/2 border-2 border-border-master bg-surface-card px-4 py-3 font-body-md text-body-md text-ink-primary shadow-brutal-md md:block"
        >
          {toast}
        </div>
      ) : null}
    </>
  );
}

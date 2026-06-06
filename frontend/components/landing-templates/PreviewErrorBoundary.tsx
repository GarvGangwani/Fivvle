"use client";

import Link from "next/link";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface PreviewErrorBoundaryProps {
  children: ReactNode;
  /** Shown in compact preview panel vs full-page published view */
  variant?: "preview" | "published";
  onRetry?: () => void;
}

interface PreviewErrorBoundaryState {
  hasError: boolean;
}

export class PreviewErrorBoundary extends Component<
  PreviewErrorBoundaryProps,
  PreviewErrorBoundaryState
> {
  state: PreviewErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): PreviewErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[Fivvle preview]", error, info.componentStack);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false });
    this.props.onRetry?.();
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const isPublished = this.props.variant === "published";

    return (
      <div
        className={
          isPublished
            ? "flex min-h-[60vh] flex-col items-center justify-center bg-[#0a0908] px-6 py-16 text-center text-[#ebe4d4]"
            : "flex min-h-[320px] flex-col items-center justify-center rounded-xl border border-amber-500/25 bg-amber-500/5 px-6 py-12 text-center"
        }
      >
        <p className="text-xs font-semibold uppercase tracking-widest text-amber-400/90">
          Preview unavailable
        </p>
        <h3
          className={`mt-3 font-semibold ${isPublished ? "text-2xl" : "text-lg text-white"}`}
        >
          We couldn&apos;t display this page
        </h3>
        <p
          className={`mt-2 max-w-md text-sm ${isPublished ? "opacity-70" : "text-zinc-400"}`}
        >
          Something in the generated content couldn&apos;t be rendered. Try
          regenerating copy from the editor, or switch design template.
        </p>
        {!isPublished && (
          <button
            type="button"
            onClick={this.handleRetry}
            className="mt-6 rounded-xl border border-white/15 px-4 py-2 text-sm text-zinc-300 hover:bg-white/5"
          >
            Try again
          </button>
        )}
        {isPublished && (
          <Link
            href="/"
            className="mt-8 rounded-full border border-white/20 px-6 py-2 text-sm hover:bg-white/5"
          >
            Back to Fivvle
          </Link>
        )}
      </div>
    );
  }
}

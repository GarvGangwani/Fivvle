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
            : "fv-card mx-4 my-8 flex min-h-[320px] flex-col items-center justify-center px-6 py-12 text-center"
        }
      >
        <p className="fv-panel-label text-[var(--fv-text-muted)]">
          Preview unavailable
        </p>
        <h3
          className={`mt-3 font-semibold ${
            isPublished ? "text-2xl" : "text-lg text-[var(--fv-text)]"
          }`}
        >
          We couldn&apos;t display this page
        </h3>
        <p
          className={`mt-2 max-w-md text-sm ${
            isPublished ? "opacity-70" : "text-[var(--fv-text-muted)]"
          }`}
        >
          Something in the generated content couldn&apos;t be rendered. Try
          editing copy fields or switching design template.
        </p>
        {!isPublished && (
          <button
            type="button"
            onClick={this.handleRetry}
            className="fv-btn-ghost mt-6 px-4 py-2 text-sm"
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

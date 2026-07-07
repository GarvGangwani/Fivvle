"use client";

import { useEffect, useRef, useState } from "react";
import { Download, FileText, Hash } from "lucide-react";
import type { ValidationReport } from "@/lib/types";
import {
  downloadValidationReportHtml,
  downloadValidationReportMarkdown,
} from "@/lib/validation-report-export";

interface ValidationReportExportMenuProps {
  report: ValidationReport;
  projectName?: string;
  /** Compact ghost button for toolbars */
  variant?: "default" | "ghost";
  className?: string;
}

export function ValidationReportExportMenu({
  report,
  projectName = "validation-report",
  variant = "default",
  className = "",
}: ValidationReportExportMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const buttonClass =
    variant === "ghost"
      ? "fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] sm:px-3"
      : "fv-btn-secondary inline-flex items-center gap-1.5 text-sm";

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        className={buttonClass}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Download report"
      >
        <Download className="h-3.5 w-3.5" />
        <span className={variant === "ghost" ? "hidden sm:inline" : undefined}>
          Download
        </span>
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-20 mt-1 min-w-[12rem] rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface)] py-1 shadow-lg"
          role="menu"
        >
          <ExportItem
            icon={FileText}
            label="Download as HTML"
            onClick={() => {
              downloadValidationReportHtml(report, projectName);
              setOpen(false);
            }}
          />
          <ExportItem
            icon={Hash}
            label="Download as Markdown"
            onClick={() => {
              downloadValidationReportMarkdown(report, projectName);
              setOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

function ExportItem({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof FileText;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[var(--fv-text)] hover:bg-[var(--fv-surface-elevated)]"
      onClick={onClick}
    >
      <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--fv-text-muted)]" />
      {label}
    </button>
  );
}

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
      ? "inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-card px-2.5 py-1.5 font-label-md text-label-sm uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md sm:px-3"
      : "inline-flex items-center gap-1.5 border-2 border-border-master bg-surface-card px-3 py-2 font-label-md text-label-md uppercase tracking-wider text-ink-primary shadow-brutal-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-md";

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
          className="absolute right-0 top-full z-20 mt-1 min-w-[12rem] border-2 border-border-master bg-surface-card py-1 shadow-brutal-md"
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
      className="flex w-full items-center gap-2 px-3 py-2 text-left font-body text-body-sm text-ink-primary transition-colors hover:bg-surface-elevated"
      onClick={onClick}
    >
      <Icon className="h-3.5 w-3.5 shrink-0 text-ink-tertiary" />
      {label}
    </button>
  );
}

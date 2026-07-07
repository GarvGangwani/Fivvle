"use client";

import { useState } from "react";
import { Download, FileJson, FileText, Printer } from "lucide-react";
import type { LandingPageV2Spec } from "@/lib/landing-page-v2-types";
import { isRuntimeSpecV4 } from "@/lib/landing-page-v2-types";

interface RuntimeExportMenuProps {
  spec: LandingPageV2Spec | null | undefined;
  projectName?: string;
}

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function RuntimeExportMenu({
  spec,
  projectName = "landing-page",
}: RuntimeExportMenuProps) {
  const [open, setOpen] = useState(false);
  const safeName = projectName.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "page";

  const exportNarrativeJson = () => {
    if (!spec || !isRuntimeSpecV4(spec)) return;
    downloadBlob(
      JSON.stringify(spec.pipeline.narrative, null, 2),
      `${safeName}-narrative.json`,
      "application/json",
    );
    setOpen(false);
  };

  const exportRuntimeSpec = () => {
    if (!spec || !isRuntimeSpecV4(spec)) return;
    downloadBlob(
      JSON.stringify(spec, null, 2),
      `${safeName}-runtime-spec.json`,
      "application/json",
    );
    setOpen(false);
  };

  const exportHtml = () => {
    const root = document.querySelector(`[data-runtime-export-root]`);
    if (!root) return;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${projectName}</title></head><body>${root.outerHTML}</body></html>`;
    downloadBlob(html, `${safeName}.html`, "text/html");
    setOpen(false);
  };

  const exportPdf = () => {
    const root = document.querySelector(`[data-runtime-export-root]`);
    if (!root) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write(`
      <!DOCTYPE html>
      <html><head>
        <meta charset="utf-8">
        <title>${projectName} — Export</title>
        <style>
          @page { size: A4; margin: 12mm; }
          body { margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        </style>
      </head><body>${root.outerHTML}</body></html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 400);
    setOpen(false);
  };

  if (!spec || !isRuntimeSpecV4(spec)) return null;

  return (
    <div className="relative">
      <button
        type="button"
        className="fv-btn-secondary inline-flex items-center gap-1.5 text-sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <Download className="h-3.5 w-3.5" />
        Export
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-20 mt-1 min-w-[12rem] rounded-lg border border-[var(--fv-border)] bg-[var(--fv-surface)] py-1 shadow-lg"
          role="menu"
        >
          <ExportItem icon={Printer} label="Export as PDF" onClick={exportPdf} />
          <ExportItem icon={FileText} label="Export as HTML" onClick={exportHtml} />
          <ExportItem icon={FileJson} label="Export Narrative JSON" onClick={exportNarrativeJson} />
          <ExportItem icon={FileJson} label="Export Runtime Spec" onClick={exportRuntimeSpec} />
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
  icon: typeof Printer;
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

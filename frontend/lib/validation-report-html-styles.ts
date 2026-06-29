/** Embedded stylesheet for standalone validation report HTML downloads. */
export const VALIDATION_REPORT_HTML_CSS = `
:root {
  --fv-accent: #4f6bff;
  --fv-on-accent: #ffffff;
  --fv-success: #22c55e;
  --fv-warning: #f59e0b;
  --fv-danger: #ef4444;
  --report-prose-width: 42rem;
}

:root,
[data-theme="dark"] {
  --fv-bg: #06080f;
  --fv-surface: #0d111c;
  --fv-surface-2: #121829;
  --fv-border: rgba(255, 255, 255, 0.06);
  --fv-border-strong: rgba(255, 255, 255, 0.11);
  --fv-text: #f1f5f9;
  --fv-text-muted: #6b7a94;
  --fv-text-soft: #9aa8be;
  --fv-text-dim: #4a5568;
  --fv-accent-muted: color-mix(in srgb, var(--fv-accent) 14%, transparent);
  --fv-body-gradient:
    radial-gradient(ellipse 100% 80% at 50% -30%, rgba(79, 107, 255, 0.08), transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(124, 92, 255, 0.05), transparent 50%);
}

[data-theme="light"] {
  --fv-bg: #f4f6fb;
  --fv-surface: #ffffff;
  --fv-surface-2: #eef1f8;
  --fv-border: rgba(15, 23, 42, 0.08);
  --fv-border-strong: rgba(15, 23, 42, 0.14);
  --fv-text: #0f172a;
  --fv-text-muted: #64748b;
  --fv-text-soft: #475569;
  --fv-text-dim: #94a3b8;
  --fv-accent-muted: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  --fv-body-gradient:
    radial-gradient(ellipse 100% 80% at 50% -30%, rgba(79, 107, 255, 0.06), transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(124, 92, 255, 0.04), transparent 50%);
}

*, *::before, *::after { box-sizing: border-box; }

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--fv-bg);
  background-image: var(--fv-body-gradient);
  color: var(--fv-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.report-page {
  max-width: 48rem;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
}

.report-canvas-article { color: var(--fv-text); }

.report-masthead {
  position: relative;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 22%, transparent);
  border-radius: 1rem;
  background:
    radial-gradient(120% 140% at 100% 0%, color-mix(in srgb, var(--fv-accent) 14%, transparent), transparent 55%),
    linear-gradient(165deg, color-mix(in srgb, var(--fv-surface-2) 92%, transparent), var(--fv-surface));
  padding: 1.5rem 1.75rem 1.75rem;
}

.report-masthead-eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-masthead-title {
  margin: 0.35rem 0 0;
  font-size: 1.6rem;
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.report-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.report-stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, white 3%, transparent);
  padding: 0.3rem 0.65rem;
  font-size: 11px;
  font-weight: 500;
  color: var(--fv-text-soft);
}

.report-stat-pill strong { font-weight: 650; color: var(--fv-text); }

.report-section-nav {
  margin: 1.25rem 0;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--fv-border);
}

.report-section-nav-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.report-section-link {
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 0.35rem 0.75rem;
  font-size: 12px;
  font-weight: 500;
  color: var(--fv-text-muted);
  text-decoration: none;
}

.report-section-link:hover {
  color: var(--fv-text);
  border-color: var(--fv-border);
  background: color-mix(in srgb, white 4%, transparent);
}

.report-block { scroll-margin-top: 1.5rem; margin-bottom: 2rem; }

.report-block-title {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin: 0 0 1rem;
  font-size: 1.05rem;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.report-block-icon {
  display: flex;
  height: 2rem;
  width: 2rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  background: var(--fv-accent-muted);
  color: var(--fv-accent);
}

.report-block-icon svg { width: 1rem; height: 1rem; stroke: currentColor; fill: none; stroke-width: 2; }

.report-card {
  border: 1px solid var(--fv-border);
  border-radius: 0.875rem;
  background: var(--fv-surface);
  padding: 1.25rem 1.35rem;
}

.report-card-accent {
  border-color: color-mix(in srgb, var(--fv-accent) 28%, transparent);
  background: linear-gradient(145deg, color-mix(in srgb, var(--fv-accent) 9%, transparent), var(--fv-surface) 45%);
}

.report-card-warning-border {
  border-color: color-mix(in srgb, var(--fv-warning) 22%, transparent);
}

.report-recommendation-badge {
  display: inline-flex;
  border-radius: 0.625rem;
  padding: 0.4rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.badge-proceed {
  background: color-mix(in srgb, var(--fv-success) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-success) 30%, transparent);
  color: var(--fv-success);
}

.badge-iterate {
  background: color-mix(in srgb, var(--fv-warning) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-warning) 30%, transparent);
  color: var(--fv-warning);
}

.badge-pivot, .badge-kill {
  background: color-mix(in srgb, var(--fv-danger) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-danger) 30%, transparent);
  color: var(--fv-danger);
}

.report-prose {
  max-width: var(--report-prose-width);
  font-size: 0.9375rem;
  line-height: 1.72;
  color: var(--fv-text-soft);
}

.report-prose p { margin: 0; }
.report-prose p + p { margin-top: 0.85em; }

.report-question {
  overflow: hidden;
  border: 1px solid var(--fv-border);
  border-radius: 0.875rem;
  background: color-mix(in srgb, var(--fv-surface-2) 80%, transparent);
  margin-bottom: 0.75rem;
}

.report-question-header {
  padding: 1rem 1.1rem;
}

.report-question-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.report-question-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.45rem;
  background: var(--fv-accent-muted);
  font-size: 11px;
  font-weight: 700;
  color: var(--fv-accent);
}

.report-question-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-question-count { font-size: 11px; color: var(--fv-text-dim); }

.report-question-score {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  border-radius: 999px;
  border: 1px solid var(--fv-border);
  padding: 0.1rem 0.45rem;
  font-size: 10px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--fv-text-soft);
  background: color-mix(in srgb, white 4%, transparent);
}

.report-question-title {
  margin: 0.45rem 0 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.45;
}

.report-question-body {
  border-top: 1px solid var(--fv-border);
  padding: 0.85rem 1.1rem 1.1rem;
}

.report-finding {
  position: relative;
  border-radius: 0.75rem;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  padding: 1rem 1rem 1rem 1.15rem;
  margin-bottom: 0.75rem;
}

.report-finding:last-child { margin-bottom: 0; }

.report-finding::before {
  content: "";
  position: absolute;
  top: 0.65rem;
  bottom: 0.65rem;
  left: 0;
  width: 3px;
  border-radius: 999px;
  background: var(--fv-border-strong);
}

.report-finding-high::before { background: var(--fv-success); }
.report-finding-medium::before { background: var(--fv-warning); }
.report-finding-low::before { background: var(--fv-text-dim); }

.report-finding-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.55rem;
}

.report-finding-index {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.fv-confidence-badge {
  display: inline-flex;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
}

.fv-confidence-high {
  background: color-mix(in srgb, var(--fv-success) 12%, transparent);
  color: var(--fv-success);
  border: 1px solid color-mix(in srgb, var(--fv-success) 25%, transparent);
}

.fv-confidence-medium {
  background: color-mix(in srgb, var(--fv-warning) 12%, transparent);
  color: var(--fv-warning);
  border: 1px solid color-mix(in srgb, var(--fv-warning) 25%, transparent);
}

.fv-confidence-low {
  background: rgba(255, 255, 255, 0.05);
  color: var(--fv-text-muted);
  border: 1px solid var(--fv-border);
}

.report-finding-claim {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.5;
}

.report-finding-evidence {
  margin-top: 0.65rem;
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--fv-text-soft);
}

.report-finding-evidence p { margin: 0; }
.report-finding-evidence p + p { margin-top: 0.65em; }

.report-finding-rationale {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--fv-text-muted);
}

.report-cite-ref {
  margin-left: 0.15rem;
  font-size: 10px;
  font-weight: 600;
  color: var(--fv-accent);
  text-decoration: none;
  vertical-align: super;
}

.report-evidence-gap {
  margin-top: 0.75rem;
  border-radius: 0.625rem;
  border: 1px solid color-mix(in srgb, var(--fv-warning) 28%, transparent);
  background: color-mix(in srgb, var(--fv-warning) 8%, transparent);
  padding: 0.75rem 0.85rem;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--fv-text-soft);
}

.report-evidence-gap strong { color: var(--fv-warning); }

.report-competitor-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
}

.report-competitor-card {
  border: 1px solid var(--fv-border);
  border-radius: 0.75rem;
  background: var(--fv-surface);
  padding: 1rem;
}

.report-competitor-name {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
}

.report-competitor-vs {
  margin: 0.75rem 0 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--fv-text-muted);
}

.report-signal-block + .report-signal-block {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--fv-border);
}

.report-signal-label {
  margin: 0;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-risk-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.report-risk-item {
  border-radius: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--fv-warning) 22%, transparent);
  background: color-mix(in srgb, var(--fv-warning) 4%, var(--fv-surface));
  padding: 1rem 1.05rem 1.1rem;
}

.report-risk-header { display: flex; align-items: flex-start; gap: 0.75rem; }

.report-risk-num {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--fv-warning) 16%, transparent);
  font-size: 11px;
  font-weight: 700;
  color: var(--fv-warning);
}

.report-risk-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.4;
}

.report-risk-verdict {
  display: inline-flex;
  margin-top: 0.4rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--fv-warning) 30%, transparent);
  background: color-mix(in srgb, var(--fv-warning) 10%, transparent);
  padding: 0.15rem 0.55rem;
  font-size: 11px;
  font-weight: 600;
  color: color-mix(in srgb, var(--fv-warning) 88%, var(--fv-text));
}

.report-risk-body {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid color-mix(in srgb, var(--fv-warning) 14%, var(--fv-border));
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--fv-text-soft);
}

.report-risk-body p { margin: 0; }
.report-risk-body p + p { margin-top: 0.65em; }

.report-risk-preamble {
  margin-bottom: 0.85rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--fv-border);
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--fv-text-soft);
}

.report-source-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.report-source-item {
  display: flex;
  gap: 0.75rem;
  border-radius: 0.625rem;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  padding: 0.65rem 0.75rem;
}

.report-source-num {
  flex-shrink: 0;
  width: 1.5rem;
  font-family: ui-monospace, monospace;
  font-size: 11px;
  font-weight: 600;
  color: var(--fv-text-muted);
}

.report-source-link {
  color: var(--fv-accent);
  text-decoration: none;
  font-size: 0.875rem;
}

.report-source-link:hover { text-decoration: underline; }

.report-source-domain {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: var(--fv-text-muted);
}

.report-footer-note {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--fv-border);
  font-size: 11px;
  color: var(--fv-text-dim);
}

.report-export-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--fv-border);
}

.report-export-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}

.report-theme-toggle {
  display: inline-flex;
  border-radius: 0.625rem;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  padding: 0.2rem;
}

.report-theme-btn {
  border: none;
  border-radius: 0.45rem;
  background: transparent;
  padding: 0.35rem 0.7rem;
  font-family: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--fv-text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.report-theme-btn:hover {
  color: var(--fv-text);
}

.report-theme-btn-active {
  background: var(--fv-accent-muted);
  color: var(--fv-accent);
}

.report-export-brand {
  font-size: 0.8rem;
  font-weight: 650;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-accent);
}

.report-export-date {
  font-size: 0.75rem;
  color: var(--fv-text-muted);
}

@media print {
  body { background: #fff; color: #111; }
  .report-section-nav,
  .report-theme-toggle { display: none; }
  .report-export-header { border-color: #ddd; }
  .report-masthead, .report-card, .report-question, .report-finding, .report-risk-item, .report-source-item, .report-competitor-card, .report-score-card, .report-score-overall {
    break-inside: avoid;
  }
}
`;

import { REPORT_SCORE_SECTION_EXPORT_CSS } from "./report-score-section-export-css";

/** Score panel styles for standalone validation report HTML downloads. */
export const VALIDATION_REPORT_SCORE_HTML_CSS = REPORT_SCORE_SECTION_EXPORT_CSS;

/** Theme toggle behavior for downloaded reports. */
export const VALIDATION_REPORT_THEME_SCRIPT = `(function(){var KEY="fivvle-report-theme";function applyTheme(theme){document.documentElement.setAttribute("data-theme",theme);document.querySelectorAll("[data-theme-btn]").forEach(function(btn){var active=btn.getAttribute("data-theme-btn")===theme;btn.classList.toggle("report-theme-btn-active",active);btn.setAttribute("aria-pressed",active?"true":"false");});}function init(){var stored=null;try{stored=localStorage.getItem(KEY);}catch(e){}var theme=stored==="light"||stored==="dark"?stored:"dark";applyTheme(theme);document.querySelectorAll("[data-theme-btn]").forEach(function(btn){btn.addEventListener("click",function(){var next=btn.getAttribute("data-theme-btn");if(!next)return;try{localStorage.setItem(KEY,next);}catch(e){}applyTheme(next);});});}if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",init);}else{init();}})();`;

/** Score card selection — mirrors in-app ReportScoreSection behavior. */
export const VALIDATION_REPORT_SCORE_SCRIPT = `(function(){function initScorePanel(panel){var selected=null;function setSelected(id){var next=selected===id?null:id;selected=next;panel.querySelectorAll("[data-score-select]").forEach(function(btn){var btnId=btn.getAttribute("data-score-select");var isSelected=btnId===selected;btn.classList.toggle("report-score-card-selected",isSelected);btn.setAttribute("aria-expanded",isSelected?"true":"false");var chevron=btn.querySelector(".report-score-chevron");if(chevron){chevron.classList.toggle("report-score-chevron-open",isSelected);}});panel.querySelectorAll("[data-score-detail]").forEach(function(mount){mount.hidden=mount.getAttribute("data-score-detail")!==selected;});}panel.querySelectorAll("[data-score-select]").forEach(function(btn){btn.addEventListener("click",function(){setSelected(btn.getAttribute("data-score-select"));});});panel.querySelectorAll("[data-score-close]").forEach(function(btn){btn.addEventListener("click",function(e){e.stopPropagation();setSelected(null);});});}function boot(){document.querySelectorAll("[data-report-score-panel]").forEach(initScorePanel);}if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",boot);}else{boot();}})();`;

# Fivvle Frontend Context

Generated for external UX redesign assistant. Source files are verbatim; secrets redacted.

## 1. Frontend orientation

### `tree -L 3 frontend` (excluding node_modules and .next)

```text
.env.local
.env.local.example
.eslintrc.json
.gitignore
app
app\(auth)
app\(auth)\.gitkeep
app\(auth)\layout.tsx
app\(auth)\login
app\(auth)\login\page.tsx
app\(auth)\signup
app\(auth)\signup\page.tsx
app\(dashboard)
app\(dashboard)\.gitkeep
app\(dashboard)\admin
app\(dashboard)\admin\cost
app\(dashboard)\admin\coupons
app\(dashboard)\archived
app\(dashboard)\archived\page.tsx
app\(dashboard)\dashboard
app\(dashboard)\dashboard\layout.tsx
app\(dashboard)\dashboard\page.tsx
app\(dashboard)\experiment
app\(dashboard)\experiment\[id]
app\(dashboard)\layout.tsx
app\(dashboard)\new
app\(dashboard)\new\page.tsx
app\(dashboard)\wallet
app\.gitkeep
app\api
app\api\revalidate
app\api\revalidate\route.ts
app\e
app\e\[slug]
app\e\[slug]\.gitkeep
app\e\[slug]\page.tsx
app\globals.css
app\icon.png
app\layout.tsx
app\page.tsx
app\preview
app\preview\device
app\preview\device\layout.tsx
app\preview\device\page.tsx
app\refinement-demos
app\refinement-demos\page.tsx
components
components\.gitkeep
components\admin
components\admin\AdminCostDashboard.tsx
components\admin\AdminCouponsDashboard.tsx
components\auth
components\auth\AuthDivider.tsx
components\auth\GoogleSignInButton.tsx
components\auth\useAuthRedirect.ts
components\auth\UserAvatar.tsx
components\chat
components\chat\ChatInput.tsx
components\chat\ChatInterface.tsx
components\chat\ChatMarkdown.tsx
components\chat\ChatMessage.tsx
components\dashboard
components\dashboard\ArchivedProjectsContent.tsx
components\dashboard\DashboardContent.tsx
components\dashboard\ExperimentCard.tsx
components\dashboard\ExperimentDetailPanel.tsx
components\dashboard\ProjectCard.tsx
components\dashboard\StatusBadge.tsx
components\distribution
components\distribution\DistributeSection.tsx
components\distribution\ShareLinksPanel.tsx
components\experiment
components\experiment\ArchiveProjectDialog.tsx
components\experiment\DeleteProjectDialog.tsx
components\experiment\EditableProjectName.tsx
components\experiment\ExperimentStageNav.tsx
components\home
components\home\distribution
components\home\HomePageContent.tsx
components\home\MarketingHero.tsx
components\insight
components\insight\DecisionPanel.tsx
components\insight\InsightReportViewer.tsx
components\insight\InsightStagePanel.tsx
components\insight\MetricsStagePanel.tsx
components\insight\MetricsWidget.tsx
components\landing-page-editor
components\landing-page-editor\CollapsibleSection.tsx
components\landing-page-editor\CopyFieldsEditor.tsx
components\landing-page-editor\DesignSlider.tsx
components\landing-page-editor\EditorLayout.tsx
components\landing-page-editor\EditorLoadingSkeleton.tsx
components\landing-page-editor\editor-panel.css
components\landing-page-editor\LandingPageSlugEditor.tsx
components\landing-page-editor\SurfaceStylePicker.tsx
components\landing-page-editor\TemplatePreviewThumb.tsx
components\landing-page-generator
components\landing-page-generator\BrandIconPicker.tsx
components\landing-page-generator\ColorThemePicker.tsx
components\landing-page-generator\device-preview.module.css
components\landing-page-generator\DevicePreview.tsx
components\landing-page-generator\DevicePreviewIframe.tsx
components\landing-page-generator\GoalSelector.tsx
components\landing-page-generator\LandingPagePreview.tsx
components\landing-page-generator\PreviewSaveStatus.tsx
components\landing-page-generator\ProgressView.tsx
components\landing-page-generator\PublishPanel.tsx
components\landing-page-generator\RegenerateButton.tsx
components\landing-page-generator\SectionEditor.tsx
components\landing-page-generator\ThemePicker.tsx
components\landing-runtime-v2
components\landing-runtime-v2\ComponentRenderer.tsx
components\landing-runtime-v2\LandingPageRuntimeWorkspace.tsx
components\landing-runtime-v2\primitives
components\landing-runtime-v2\primitives\VisualPrimitives.tsx
components\landing-runtime-v2\RuntimeAnalytics.tsx
components\landing-runtime-v2\RuntimeExportMenu.tsx
components\landing-runtime-v2\RuntimeRenderer.tsx
components\landing-runtime-v2\runtime-v2.module.css
components\landing-runtime-v2\sections
components\landing-runtime-v2\spacingScale.ts
components\landing-runtime-v2\themeTokens.ts
components\landing-templates
components\landing-templates\.gitkeep
components\landing-templates\abstract.module.css
components\landing-templates\AbstractTemplate.tsx
components\landing-templates\aether.module.css
components\landing-templates\AetherTemplate.tsx
components\landing-templates\bold-v1.module.css
components\landing-templates\BoldV1Template.tsx
components\landing-templates\brand-mark.module.css
components\landing-templates\BrandMark.tsx
components\landing-templates\CopyEditContext.tsx
components\landing-templates\CopyText.tsx
components\landing-templates\CtaAction.tsx
components\landing-templates\dark-premium.module.css
components\landing-templates\DarkPremiumTemplate.tsx
components\landing-templates\editable-copy.module.css
components\landing-templates\EditableCopy.tsx
components\landing-templates\editorial-saas.module.css
components\landing-templates\EditorialSaasTemplate.tsx
components\landing-templates\minimal-v3.module.css
components\landing-templates\MinimalV3Template.tsx
components\landing-templates\PreviewErrorBoundary.tsx
components\landing-templates\section-image-slot.module.css
components\landing-templates\SectionImageSlot.tsx
components\landing-templates\surface-overlay.module.css
components\landing-templates\SurfaceShell.tsx
components\landing-templates\template-base.module.css
components\landing-templates\TemplateRenderer.tsx
components\landing-templates\template-shared.ts
components\landing-templates\useScrollReveal.ts
components\layout
components\layout\AppHeader.tsx
components\layout\DashboardShell.tsx
components\layout\FivvleLogo.tsx
components\layout\FivvleShell.tsx
components\layout\ShellSidebar.tsx
components\providers
components\providers\AppProviders.tsx
components\published
components\published\PublishedLandingPage.tsx
components\published\WaitlistForm.tsx
components\refinement
components\refinement\ClarifyingQuestionBlock.tsx
components\refinement\ClarifyingQuestionsLoading.tsx
components\refinement\ClarityAnswerCarousel.tsx
components\refinement\guided
components\refinement\legacy
components\refinement\PressureTestSection.tsx
components\refinement\refinement-ascent.css
components\refinement\refinement-thread.css
components\refinement\RefinementThreadMessage.tsx
components\refinement\RefineStagePanel.tsx
components\refinement-demos
components\refinement-demos\BlueprintBuilderDemo.tsx
components\refinement-demos\CardDraftDemo.tsx
components\refinement-demos\ConfidenceDuelDemo.tsx
components\refinement-demos\EvidenceBoardDemo.tsx
components\refinement-demos\IdeaStatsDemo.tsx
components\refinement-demos\index.ts
components\refinement-demos\PitchDeckDemo.tsx
components\refinement-demos\quest-map
components\refinement-demos\quest-map\index.ts
components\refinement-demos\quest-map\quest-map.css
components\refinement-demos\quest-map\quest-map-data.ts
components\refinement-demos\quest-map\QuestMapExperience.tsx
components\refinement-demos\QuestMapDemo.tsx
components\refinement-demos\RefinementAscentDemo.tsx
components\refinement-demos\refinement-demos.css
components\refinement-demos\RefinementDemoShowcase.tsx
components\refinement-demos\RefinementPeakDemo.tsx
components\refinement-demos\shared.ts
components\research
components\research\InlineResearchProgress.tsx
components\research\LandingGenerationProgress.tsx
components\research\PhaseIndicator.tsx
components\research\report-canvas.css
components\research\ReportCanvas.tsx
components\research\report-score-section.css
components\research\ReportScoreSection.tsx
components\research\ResearchActivityFeed.tsx
components\research\ResearchProgress.tsx
components\research\TemplatePicker.tsx
components\research\useResearchActivityLog.ts
components\research\ValidationReportExportMenu.tsx
components\research\ValidationReportPanel.tsx
components\research\ValidationReportViewer.tsx
components\settings
components\settings\AuthSettingsCorner.tsx
components\settings\SettingsButton.tsx
components\settings\SettingsPanel.tsx
components\settings\WalletTransactionHistory.tsx
components\ui
components\ui\EmptyState.tsx
components\ui\ErrorBanner.tsx
components\ui\LoadingState.tsx
components\ui\PageHeader.tsx
components\ui\ToastProvider.tsx
components\ui\TypeConfirmDialog.tsx
components\wallet
components\wallet\BuyCreditsFlow.tsx
components\wallet\CouponRedemption.tsx
components\wallet\InsightPaywallModal.tsx
components\wallet\InsightUnlockPrompt.tsx
components\wallet\MetricsAnalysisPrompt.tsx
components\wallet\MetricsPaywallModal.tsx
components\wallet\RazorpayBrand.tsx
components\wallet\useInsightPaywallGate.tsx
components\wallet\useMetricsPaywallGate.tsx
components\wallet\useValidationPaywallGate.tsx
components\wallet\ValidationPaywallModal.tsx
components\wallet\ValidationResearchPrompt.tsx
components\wallet\WalletModal.tsx
components\wallet\WalletTrigger.tsx
docs
docs\LANDING_PAGE_SUBDOMAINS.md
lib
lib\.gitkeep
lib\__tests__
lib\__tests__\report-text.test.ts
lib\api.ts
lib\auth-context.tsx
lib\auth-errors.ts
lib\branding.ts
lib\clarifying-questions.ts
lib\color-palettes.ts
lib\copy-limits.ts
lib\copy-mutations.ts
lib\coupon-errors.ts
lib\cta-config.ts
lib\device-presets.ts
lib\device-preview-messages.ts
lib\experiment-events.ts
lib\experiment-name.ts
lib\experiment-stages.ts
lib\export-page.ts
lib\firebase.ts
lib\format-time.ts
lib\insight-flow.ts
lib\landing-flow.ts
lib\landing-host.ts
lib\landing-page-data.ts
lib\landing-page-sections.ts
lib\landing-page-v2-types.ts
lib\metrics-flow.ts
lib\normalize-copy.ts
lib\preferences-context.tsx
lib\pricing.ts
lib\published-page.ts
lib\razorpay-checkout.ts
lib\refinement-thread.ts
lib\report-score-section-export-css.ts
lib\report-text.ts
lib\research-activity.ts
lib\research-status.ts
lib\section-images.ts
lib\session-expired.ts
lib\sidebar-context.tsx
lib\smooth-scroll.ts
lib\surface.ts
lib\template-preview-page.ts
lib\templates.ts
lib\types.ts
lib\user-avatar.ts
lib\validation-flow.ts
lib\validation-report-export.ts
lib\validation-report-html-styles.ts
lib\validation-report-score-details.ts
lib\validation-report-score-html.ts
lib\validation-report-scores.ts
lib\wallet-context.tsx
lib\wallet-errors.ts
lib\wallet-paywall.ts
lib\wallet-sync.ts
lib\wallet-transactions.ts
middleware.ts
next.config.js
next-env.d.ts
package.json
package-lock.json
postcss.config.js
public
public\.gitkeep
public\fivvle-icon.png
README.md
tailwind.config.ts
tsconfig.json
tsconfig.tsbuildinfo
types
types\.gitkeep
types\razorpay.d.ts
vitest.config.ts
```

### `package.json`

```json
{
  "name": "fivvle-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "clean": "node -e \"const fs=require('fs'),path=require('path');['.next','node_modules/.cache/fivvle-next-dev'].forEach(p=>{try{fs.rmSync(path.join(process.cwd(),p),{recursive:true,force:true})}catch(e){}})\"",
    "dev": "next dev",
    "dev:clean": "npm run clean && next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "autoprefixer": "10.5.0",
    "firebase": "12.13.0",
    "lucide-react": "1.14.0",
    "next": "15.5.18",
    "postcss": "8.5.14",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "react-markdown": "10.1.0",
    "remark-gfm": "4.0.1",
    "tailwindcss": "3.4.19",
    "typescript": "5.9.3"
  },
  "devDependencies": {
    "@types/node": "22.19.18",
    "@types/react": "19.0.0",
    "@types/react-dom": "19.0.0",
    "eslint": "8.57.1",
    "eslint-config-next": "15.5.18",
    "vitest": "^3.2.4"
  }
}
```

### `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        fv: {
          bg: "var(--fv-bg)",
          surface: "var(--fv-surface)",
          text: "var(--fv-text)",
          "text-muted": "var(--fv-text-muted)",
          "text-soft": "var(--fv-text-soft)",
          "text-dim": "var(--fv-text-dim)",
          inactive: "var(--fv-inactive)",
          accent: "var(--fv-accent)",
          "accent-hover": "var(--fv-accent-hover)",
          success: "var(--fv-success)",
          warning: "var(--fv-warning)",
          danger: "var(--fv-danger)",
          "on-accent": "var(--fv-on-accent)",
          border: "var(--fv-border)",
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

### `next.config.js`

```javascript
/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV !== "production";

// CSP is environment-aware for two reasons:
//
// 1. 'unsafe-eval' in script-src: Next.js React Fast Refresh (HMR) evaluates
//    strings at runtime in development. This is safe in dev because no
//    untrusted code runs locally, but must be absent in production to prevent
//    XSS via eval-based injection.
//
// 2. localhost origins in connect-src: The frontend dev server (localhost:3000)
//    opens a WebSocket to itself for HMR, and the app calls the FastAPI backend
//    at localhost:8000 during local development. Neither origin exists in
//    production, so both are dev-only allowlist entries.
//    TODO: Once the production API domain is confirmed (e.g. https://api.fivvle.io),
//    add it to the production connect-src below.

// Google Sign-In (Firebase popup/redirect) requires these origins in CSP.
const googleAuthScriptSrc =
  "https://apis.google.com https://www.gstatic.com";
const googleAuthFrameSrc =
  "https://accounts.google.com https://*.google.com https://*.firebaseapp.com";
const googleAuthConnectSrc =
  "https://accounts.google.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://www.googleapis.com";

// Razorpay Checkout overlay (script + payment iframe).
const razorpayScriptSrc = "https://checkout.razorpay.com";
const razorpayFrameSrc = "https://api.razorpay.com https://checkout.razorpay.com";

const csp = isDev
  ? "default-src 'self'; " +
    `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${googleAuthScriptSrc} ${razorpayScriptSrc}; ` +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https: http://localhost:8000 http://127.0.0.1:8000; " +
    `frame-src 'self' ${googleAuthFrameSrc} ${razorpayFrameSrc}; ` +
    `connect-src 'self' http://localhost:8000 ws://localhost:3000 ws://localhost:3001 http://localhost:3001 https://*.googleapis.com https://*.firebaseapp.com https://*.firebaseio.com ${googleAuthConnectSrc}`
  : "default-src 'self'; " +
    `script-src 'self' 'unsafe-inline' ${googleAuthScriptSrc} ${razorpayScriptSrc}; ` +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https: https://firebasestorage.googleapis.com; " +
    `frame-src 'self' ${googleAuthFrameSrc} ${razorpayFrameSrc}; ` +
    `connect-src 'self' https://*.googleapis.com https://*.firebaseapp.com https://*.firebaseio.com ${googleAuthConnectSrc}`;

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

// Editor device preview embeds this route in a same-origin iframe.
const previewDeviceHeaders = securityHeaders.map((header) =>
  header.key === "X-Frame-Options"
    ? { key: "X-Frame-Options", value: "SAMEORIGIN" }
    : header,
);

// Public landing pages use per-project subdomains ({slug}.fivvle.io). Middleware
// rewrites those hosts to /e/[slug]. See frontend/docs/LANDING_PAGE_SUBDOMAINS.md.

const path = require("path");

// Dev cache under node_modules (relative path required by Next) so OneDrive does not
// corrupt vendor-chunks / build-manifest.json while `next dev` is running.
const devDistDir = "node_modules/.cache/fivvle-next-dev";

module.exports = {
  // Prevent Next from picking up C:\Users\Admin\package-lock.json as the monorepo root.
  outputFileTracingRoot: path.join(__dirname),
  ...(isDev ? { distDir: devDistDir } : {}),
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
      {
        source: "/preview/device",
        headers: previewDeviceHeaders,
      },
    ];
  },
};
```

### `app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --fv-accent: #4f6bff;
  --fv-accent-hover: #6b84ff;
  --fv-accent-gradient-end: #7c5cff;
  --fv-on-accent: #ffffff;
  --fv-success: #22c55e;
  --fv-warning: #f59e0b;
  --fv-danger: #ef4444;
  --fv-radius-sm: 8px;
  --fv-radius-md: 12px;
  --fv-radius-lg: 16px;
  --fv-radius-xl: 20px;
}

:root,
[data-theme="dark"] {
  --fv-bg: #06080f;
  --fv-surface: #0d111c;
  --fv-surface-2: #121829;
  --fv-surface-elevated: #182035;
  --fv-border: rgba(255, 255, 255, 0.06);
  --fv-border-strong: rgba(255, 255, 255, 0.11);
  --fv-text: #f1f5f9;
  --fv-text-muted: #6b7a94;
  --fv-text-soft: #9aa8be;
  --fv-text-dim: #4a5568;
  --fv-inactive: #2a3347;
  --fv-accent-muted: color-mix(in srgb, var(--fv-accent) 14%, transparent);
  --fv-danger-light: #fca5a5;
  --fv-header-bg: rgba(8, 12, 20, 0.9);
  --fv-skeleton-base: rgba(255, 255, 255, 0.03);
  --fv-skeleton-shine: rgba(255, 255, 255, 0.07);
  --fv-hover-overlay: rgba(255, 255, 255, 0.04);
  --background: var(--fv-bg);
  --foreground: var(--fv-text);
}

[data-theme="light"] {
  --fv-bg: #f4f6fb;
  --fv-surface: #ffffff;
  --fv-surface-2: #eef1f8;
  --fv-surface-elevated: #ffffff;
  --fv-border: rgba(15, 23, 42, 0.08);
  --fv-border-strong: rgba(15, 23, 42, 0.14);
  --fv-text: #0f172a;
  --fv-text-muted: #64748b;
  --fv-text-soft: #475569;
  --fv-text-dim: #94a3b8;
  --fv-inactive: #cbd5e1;
  --fv-accent-hover: #3d58e8;
  --fv-accent-muted: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  --fv-danger-light: #dc2626;
  --fv-header-bg: rgba(255, 255, 255, 0.88);
  --fv-skeleton-base: rgba(15, 23, 42, 0.04);
  --fv-skeleton-shine: rgba(15, 23, 42, 0.08);
  --fv-hover-overlay: rgba(15, 23, 42, 0.04);
  --background: var(--fv-bg);
  --foreground: var(--fv-text);
}

* {
  box-sizing: border-box;
}

html {
  height: 100%;
  overflow-x: hidden;
}

body {
  min-height: 100%;
  min-width: 0;
  overflow-x: hidden;
  background: var(--fv-bg);
  background-image:
    radial-gradient(ellipse 100% 80% at 50% -30%, rgba(79, 107, 255, 0.08), transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(124, 92, 255, 0.05), transparent 50%);
  color: var(--fv-text);
  font-family: var(--font-inter), system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

[data-theme="light"] body {
  background-image:
    radial-gradient(ellipse 100% 80% at 50% -30%, rgba(79, 107, 255, 0.06), transparent 60%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(124, 92, 255, 0.04), transparent 50%);
}

/* Public founder landing pages — no Fivvle dashboard chrome bleeding through */
body:has([data-fivvle-public-landing]) {
  background: #ffffff;
  background-image: none;
  color: #111111;
}

.fv-shell-header {
  background: var(--fv-header-bg);
  backdrop-filter: blur(12px);
}

.fv-wallet-balance {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, var(--fv-surface-2) 88%, transparent);
  user-select: none;
  cursor: pointer;
  font: inherit;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.fv-wallet-balance:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 35%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 6%, var(--fv-surface-2));
}

.fv-wallet-balance:focus-visible {
  outline: 2px solid var(--fv-accent);
  outline-offset: 2px;
}

.fv-wallet-balance-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--fv-accent);
}

.fv-wallet-balance-credits {
  font-size: 12px;
  font-weight: 600;
  color: var(--fv-text);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  line-height: 1.2;
}

.fv-wallet-modal {
  border-radius: var(--fv-radius-lg);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
}

.fv-wallet-balance-card {
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid var(--fv-border);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--fv-accent) 10%, var(--fv-surface-2)),
    var(--fv-surface-2)
  );
}

.fv-wallet-balance-card-label {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.fv-wallet-balance-card-credits {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--fv-text);
  font-variant-numeric: tabular-nums;
}

.fv-wallet-balance-card-usd {
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--fv-text-muted);
}

.fv-wallet-pack-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.fv-wallet-pack-row-popular {
  border-color: color-mix(in srgb, var(--fv-accent) 40%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 5%, var(--fv-surface-2));
}

.fv-wallet-pack-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--fv-accent);
  background: var(--fv-accent-muted);
}

.fv-wallet-pack-buy {
  border-radius: 10px;
  white-space: nowrap;
}

.fv-wallet-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  font-size: 12px;
  font-weight: 500;
  color: var(--fv-text-muted);
  cursor: pointer;
  transition: color 0.15s ease;
}

.fv-wallet-back-btn:hover:not(:disabled) {
  color: var(--fv-text);
}

.fv-wallet-back-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fv-wallet-checkout-card {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.fv-wallet-checkout-summary {
  margin: 0;
  padding-top: 12px;
  border-top: 1px solid var(--fv-border);
}

.fv-wallet-checkout-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--fv-text-muted);
}

.fv-wallet-checkout-row + .fv-wallet-checkout-row {
  margin-top: 8px;
}

.fv-wallet-checkout-row dt {
  margin: 0;
  font-weight: 500;
}

.fv-wallet-checkout-row dd {
  margin: 0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--fv-text);
}

.fv-wallet-checkout-row-total {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--fv-border);
  font-size: 14px;
}

.fv-wallet-checkout-row-total dt,
.fv-wallet-checkout-row-total dd {
  color: var(--fv-text);
  font-weight: 700;
}

.fv-wallet-buy-confirm {
  min-height: 40px;
}

.fv-wallet-success-icon {
  background: color-mix(in srgb, var(--fv-success) 12%, transparent);
}

.fv-wallet-coupon-form {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.fv-wallet-coupon-input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
}

.fv-wallet-coupon-input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  width: 14px;
  height: 14px;
  transform: translateY(-50%);
  color: var(--fv-text-dim);
  pointer-events: none;
}

.fv-wallet-coupon-input {
  padding: 10px 12px 10px 34px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.fv-wallet-coupon-input::placeholder {
  text-transform: none;
  letter-spacing: normal;
  color: var(--fv-text-dim);
}

.fv-wallet-coupon-redeem {
  min-height: 42px;
  border-radius: 12px;
}

.fv-wallet-coupon-success {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--fv-success) 30%, transparent);
  background: color-mix(in srgb, var(--fv-success) 10%, transparent);
}

.fv-validation-paywall-include {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.fv-validation-paywall-include-icon {
  display: flex;
  height: 32px;
  width: 32px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, var(--fv-accent) 8%, var(--fv-surface));
  color: var(--fv-accent);
}

.fv-validation-paywall-cost {
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 25%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 6%, var(--fv-surface-2));
}

.fv-validation-research-prompt {
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 35%, transparent);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--fv-accent) 12%, var(--fv-surface-2)),
    var(--fv-surface-2)
  );
}

.fv-validation-research-prompt-icon {
  display: flex;
  height: 40px;
  width: 40px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 30%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 10%, transparent);
  color: var(--fv-accent);
}

[data-reduced-motion="true"] *,
[data-reduced-motion="true"] *::before,
[data-reduced-motion="true"] *::after {
  animation-duration: 0.01ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.01ms !important;
  scroll-behavior: auto !important;
}

::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--fv-inactive);
  border-radius: 2px;
}

@keyframes fv-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes fv-pulse-dot {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

@keyframes fv-msg-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fv-msg-enter {
  animation: fv-msg-enter 300ms ease-out both;
}

@keyframes fv-fade-up {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fv-fade-up {
  animation: fv-fade-up 600ms ease-out both;
}

.fv-fade-up-delay {
  animation: fv-fade-up 600ms ease-out 150ms both;
}

.fv-tab-pill {
  padding: 6px 20px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  transition: all 0.2s;
  background: transparent;
  color: var(--fv-text-muted);
  text-transform: capitalize;
}

.fv-tab-pill:hover {
  color: var(--fv-text);
}

.fv-tab-pill-active {
  background: var(--fv-accent-muted);
  color: var(--fv-accent);
}

.fv-sidebar-item {
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 2px;
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: background 200ms ease, border-color 200ms ease;
}

.fv-sidebar-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.fv-sidebar-item-active {
  background: color-mix(in srgb, var(--fv-accent) 10%, transparent);
  border-left-color: var(--fv-accent);
}

.fv-shell-sidebar {
  width: var(--fv-sidebar-width, 260px);
  transition: width 280ms cubic-bezier(0.16, 1, 0.3, 1);
  will-change: width;
}

.fv-shell-sidebar-expanded {
  --fv-sidebar-width: 260px;
}

.fv-shell-sidebar-collapsed {
  --fv-sidebar-width: 72px;
}

.fv-card {
  background: var(--fv-surface-2);
  border: 1px solid var(--fv-border);
  border-radius: 14px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04) inset,
    0 8px 24px rgba(0, 0, 0, 0.35);
  min-width: 0;
}

.fv-card-hover {
  transition: border-color 200ms ease, background 200ms ease,
    box-shadow 200ms ease, transform 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.fv-card-hover:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 30%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 4%, transparent);
  cursor: pointer;
  transform: translateY(-2px);
  box-shadow: 0 8px 30px -4px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.fv-card-selected {
  border-color: var(--fv-accent);
  background: color-mix(in srgb, var(--fv-accent) 8%, transparent);
}

.fv-btn-primary {
  background: var(--fv-accent);
  border: none;
  border-radius: 12px;
  color: var(--fv-on-accent);
  font-weight: 600;
  cursor: pointer;
  transition: background 200ms ease, transform 200ms cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 200ms ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(61, 89, 254, 0.2);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: inherit;
  min-width: 0;
}

.fv-btn-primary:hover:not(:disabled) {
  background: var(--fv-accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 20px rgba(61, 89, 254, 0.3);
}

.fv-btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fv-btn-ghost {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--fv-border-strong);
  border-radius: 8px;
  color: var(--fv-text-soft);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.fv-btn-ghost:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--fv-text);
}

.fv-input {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: var(--fv-text);
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
  min-width: 0;
}

.fv-input:focus {
  border-color: color-mix(in srgb, var(--fv-accent) 50%, transparent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--fv-accent) 18%, transparent);
  outline: none;
}

.fv-msg-user {
  font-size: 15px;
  line-height: 1.65;
  color: var(--fv-text);
}

.fv-msg-ai {
  font-size: 15px;
  line-height: 1.65;
  color: var(--fv-text);
}

.fv-chat-md {
  font-size: 15px;
  line-height: 1.65;
  color: var(--fv-text);
}

.fv-chat-md > :first-child {
  margin-top: 0;
}

.fv-chat-md > :last-child {
  margin-bottom: 0;
}

.fv-chat-md p {
  margin: 0.65em 0;
}

.fv-chat-md p:first-child {
  margin-top: 0;
}

.fv-chat-md strong {
  font-weight: 600;
  color: var(--fv-text);
}

.fv-chat-md ul,
.fv-chat-md ol {
  margin: 0.65em 0;
  padding-left: 1.35em;
}

.fv-chat-md ul {
  list-style-type: disc;
}

.fv-chat-md ol {
  list-style-type: decimal;
}

.fv-chat-md li {
  margin: 0.35em 0;
}

.fv-chat-md li > p {
  margin: 0.25em 0;
}

.fv-chat-md h1,
.fv-chat-md h2,
.fv-chat-md h3,
.fv-chat-md h4 {
  margin: 1em 0 0.5em;
  font-weight: 600;
  line-height: 1.35;
  color: var(--fv-text);
}

.fv-chat-md h1 {
  font-size: 1.25em;
}

.fv-chat-md h2 {
  font-size: 1.15em;
}

.fv-chat-md h3,
.fv-chat-md h4 {
  font-size: 1.05em;
}

.fv-chat-md a {
  color: var(--fv-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.fv-chat-md a:hover {
  opacity: 0.85;
}

.fv-chat-md code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.9em;
  background: color-mix(in srgb, var(--fv-text) 8%, transparent);
  border-radius: 4px;
  padding: 0.1em 0.35em;
}

.fv-chat-md pre {
  margin: 0.75em 0;
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
  padding: 0.75em 1em;
}

.fv-chat-md pre code {
  background: none;
  padding: 0;
}

.fv-chat-md blockquote {
  margin: 0.75em 0;
  padding-left: 1em;
  border-left: 3px solid var(--fv-border);
  color: var(--fv-text-soft);
}

.fv-chat-md hr {
  margin: 1em 0;
  border: none;
  border-top: 1px solid var(--fv-border);
}

.fv-chat-md table {
  width: 100%;
  margin: 0.75em 0;
  border-collapse: collapse;
  font-size: 0.92em;
}

.fv-chat-md th,
.fv-chat-md td {
  border: 1px solid var(--fv-border);
  padding: 0.45em 0.65em;
  text-align: left;
  vertical-align: top;
}

.fv-chat-md th {
  font-weight: 600;
  background: color-mix(in srgb, var(--fv-text) 6%, transparent);
  color: var(--fv-text);
}

.fv-chat-md tr:nth-child(even) td {
  background: color-mix(in srgb, var(--fv-text) 3%, transparent);
}

.fv-deep-toggle {
  border: 1px solid color-mix(in srgb, var(--fv-accent) 30%, transparent);
  border-radius: 8px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  background: transparent;
  color: var(--fv-text-muted);
}

.fv-deep-toggle-on {
  background: var(--fv-accent-muted);
  border-color: var(--fv-accent);
  color: var(--fv-accent);
}

.fv-deep-toggle:hover {
  border-color: var(--fv-accent);
  color: var(--fv-accent);
}

.fv-icon-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--fv-text-muted);
}

.fv-icon-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--fv-text-soft);
}

.fv-send-btn {
  background: var(--fv-accent);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--fv-on-accent);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fv-send-btn:hover:not(:disabled) {
  background: var(--fv-accent-hover);
  transform: scale(1.04);
}

.fv-send-btn:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: var(--fv-text-dim);
  cursor: not-allowed;
  transform: none;
}

.fv-q-option {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 14px;
}

.fv-q-option:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 40%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 6%, transparent);
}

.fv-q-option-selected {
  border-color: var(--fv-accent);
  background: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  color: var(--fv-accent);
}

.fv-panel-label {
  font-size: 11px;
  color: var(--fv-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600;
}

.fv-wallet-tx-stat {
  border-radius: 12px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
  padding: 10px 12px;
}

.fv-wallet-tx-stat-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fv-text-muted);
}

.fv-wallet-tx-stat-value {
  margin-top: 4px;
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--fv-text);
}

.fv-wallet-tx-row {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
}

.fv-wallet-tx-scroll {
  max-height: 21.5rem;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: var(--fv-border-strong) transparent;
}

.fv-wallet-tx-scroll::-webkit-scrollbar {
  width: 6px;
}

.fv-wallet-tx-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.fv-wallet-tx-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: var(--fv-border-strong);
}

.fv-wallet-tx-icon {
  display: flex;
  height: 36px;
  width: 36px;
  shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid var(--fv-border);
}

.fv-wallet-tx-icon-credit {
  background: color-mix(in srgb, var(--fv-success) 12%, transparent);
  color: var(--fv-success);
  border-color: color-mix(in srgb, var(--fv-success) 22%, transparent);
}

.fv-wallet-tx-icon-debit {
  background: var(--fv-surface);
  color: var(--fv-text-soft);
}

.fv-error {
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--fv-danger) 30%, transparent);
  background: color-mix(in srgb, var(--fv-danger) 10%, transparent);
  padding: 12px 16px;
  font-size: 14px;
  color: var(--fv-danger-light);
}

.fv-accent-ring:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--fv-accent) 50%, transparent);
  outline-offset: 2px;
}

/* Stage progress dots */
.stage-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stage-dot.done {
  background: var(--fv-success);
}

.stage-dot.active {
  background: var(--fv-accent);
  animation: fv-pulse-dot 1.5s ease-in-out infinite;
}

.stage-dot.pending {
  background: var(--fv-inactive);
}

/* Legacy message content aliases — flat conversational style */
.msg-bubble-user {
  font-size: 15px;
  line-height: 1.65;
  color: var(--fv-text);
}

.msg-bubble-ai {
  font-size: 15px;
  line-height: 1.65;
  color: var(--fv-text);
}

.report-tab {
  padding: 8px 14px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--fv-text-dim);
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.report-tab:hover {
  color: var(--fv-text-soft);
}

.report-tab.active {
  background: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  color: var(--fv-accent);
}

.badge-proceed {
  background: color-mix(in srgb, var(--fv-success) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-success) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-success);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  text-transform: uppercase;
}

.badge-iterate {
  background: color-mix(in srgb, var(--fv-warning) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-warning) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-warning);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  text-transform: uppercase;
}

.badge-pivot {
  background: color-mix(in srgb, var(--fv-danger) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-danger) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-danger);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  text-transform: uppercase;
}

.badge-kill {
  background: color-mix(in srgb, var(--fv-danger) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-danger) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-danger);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  text-transform: uppercase;
}

.host-card {
  background: var(--fv-surface-2);
  border: 1px solid var(--fv-border);
  border-radius: 14px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.15s;
}

.host-card:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 30%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 4%, transparent);
}

.host-card.selected {
  border-color: var(--fv-accent);
  background: color-mix(in srgb, var(--fv-accent) 8%, transparent);
}

.host-btn {
  background: var(--fv-accent);
  border: none;
  border-radius: 12px;
  color: var(--fv-on-accent);
  cursor: pointer;
  font-family: inherit;
  font-weight: 600;
  padding: 12px 20px;
  transition: all 0.2s;
  width: 100%;
}

.host-btn:hover:not(:disabled) {
  background: var(--fv-accent-hover);
}

.host-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.q-option {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 14px;
}

.q-option:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 40%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 6%, transparent);
}

.q-option.selected {
  border-color: var(--fv-accent);
  background: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  color: var(--fv-accent);
}

.severity-high {
  background: color-mix(in srgb, var(--fv-danger) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-danger) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-danger);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
}

.severity-medium {
  background: color-mix(in srgb, var(--fv-warning) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-warning) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-warning);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
}

.severity-low {
  background: color-mix(in srgb, var(--fv-success) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--fv-success) 30%, transparent);
  border-radius: 5px;
  color: var(--fv-success);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
}

.unavailable-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  color: var(--fv-text-dim);
  font-size: 11px;
  padding: 2px 8px;
}

.analytics-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 16px;
}

.icon-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--fv-text-muted);
}

.icon-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--fv-text-soft);
}

.fv-new-idea-btn {
  width: 100%;
  padding: 9px 14px;
  background: color-mix(in srgb, var(--fv-accent) 10%, transparent);
  border: 1px dashed color-mix(in srgb, var(--fv-accent) 30%, transparent);
  border-radius: 10px;
  color: var(--fv-accent);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s;
  font-family: inherit;
  text-decoration: none;
}

.fv-new-idea-btn:hover {
  background: color-mix(in srgb, var(--fv-accent) 15%, transparent);
  border-color: color-mix(in srgb, var(--fv-accent) 50%, transparent);
}

.fv-stage-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--fv-accent);
  border-top-color: transparent;
  border-radius: 50%;
  animation: fv-spin 0.8s linear infinite;
  flex-shrink: 0;
}

/* Horizontal research phase progress bar */
.fv-phase-bar {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  width: 100%;
}

.fv-phase-bar-track {
  position: relative;
  padding: 0.625rem 0 1.75rem;
}

.fv-phase-bar-fill {
  position: absolute;
  left: 0;
  top: calc(0.625rem + 9px);
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    var(--fv-accent),
    color-mix(in srgb, var(--fv-accent) 70%, var(--fv-success))
  );
  transition: width 0.45s ease;
  pointer-events: none;
  z-index: 0;
}

.fv-phase-bar-track::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: calc(0.625rem + 9px);
  height: 3px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--fv-text) 10%, transparent);
  z-index: 0;
}

.fv-phase-bar-nodes {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 0.25rem;
}

.fv-phase-bar-node {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.fv-phase-bar-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--fv-border-strong);
  background: var(--fv-surface-elevated);
  color: var(--fv-text-muted);
  flex-shrink: 0;
  transition: border-color 0.2s, background 0.2s, color 0.2s, box-shadow 0.2s;
}

.fv-phase-bar-dot--completed {
  border-color: var(--fv-success);
  background: color-mix(in srgb, var(--fv-success) 14%, var(--fv-surface-elevated));
  color: var(--fv-success);
}

.fv-phase-bar-dot--active {
  border-color: var(--fv-accent);
  background: color-mix(in srgb, var(--fv-accent) 16%, var(--fv-surface-elevated));
  color: var(--fv-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--fv-accent) 18%, transparent);
}

.fv-phase-bar-dot--pending {
  border-color: color-mix(in srgb, var(--fv-text) 14%, transparent);
  background: var(--fv-surface-2);
}

.fv-phase-bar-node-label {
  max-width: 100%;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-align: center;
  line-height: 1.2;
  color: var(--fv-text-dim);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fv-phase-bar-node-label--completed {
  color: var(--fv-success);
}

.fv-phase-bar-node-label--active {
  color: var(--fv-accent);
}

.fv-phase-bar-caption {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
}

.fv-research-activity {
  margin-top: 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, var(--fv-surface) 92%, var(--fv-bg));
  overflow: hidden;
}

.fv-research-activity-title {
  margin: 0;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--fv-border);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.fv-research-activity-scroll {
  max-height: 11rem;
  overflow-y: auto;
  padding: 0.55rem 0.65rem;
}

.fv-research-activity-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.fv-research-activity-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 13px;
  line-height: 1.45;
  animation: fv-research-activity-in 0.28s ease-out;
}

@keyframes fv-research-activity-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fv-research-activity-item--done {
  color: var(--fv-text-muted);
}

.fv-research-activity-item--active {
  color: var(--fv-text);
}

.fv-research-activity-icon {
  display: inline-flex;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.fv-research-activity-item--done .fv-research-activity-icon {
  color: var(--fv-success);
}

.fv-research-activity-item--active .fv-research-activity-icon {
  color: var(--fv-accent);
}

.fv-research-activity-text {
  min-width: 0;
}

@media (max-width: 480px) {
  .fv-phase-bar-node-label {
    font-size: 9px;
  }

  .fv-phase-bar-dot {
    width: 18px;
    height: 18px;
  }
}

.fv-refining-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--fv-warning) 10%, transparent);
  color: var(--fv-warning);
  border: 1px solid color-mix(in srgb, var(--fv-warning) 20%, transparent);
}

.fv-f-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(
    135deg,
    var(--fv-accent),
    var(--fv-accent-gradient-end)
  );
  color: var(--fv-on-accent);
  font-weight: 700;
  flex-shrink: 0;
}

@keyframes fv-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.fv-skeleton {
  background: linear-gradient(
    90deg,
    var(--fv-skeleton-base) 25%,
    var(--fv-skeleton-shine) 50%,
    var(--fv-skeleton-base) 75%
  );
  background-size: 200% 100%;
  animation: fv-shimmer 1.4s ease-in-out infinite;
}

/* Stage navigation tabs */
.fv-stage-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--fv-text-muted);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.fv-stage-tab:hover:not(:disabled) {
  color: var(--fv-text);
  background: var(--fv-hover-overlay);
}

.fv-stage-tab-active {
  background: var(--fv-accent-muted);
  color: var(--fv-accent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--fv-accent) 25%, transparent);
}

.fv-stage-tab-locked {
  opacity: 0.35;
  cursor: not-allowed;
}

.fv-experiment-stage-nav .fv-stage-tab {
  padding: 8px 12px;
  font-size: 12px;
}

/* Report & content sections */
.fv-section-card {
  background: var(--fv-surface-2);
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-lg);
  padding: 24px;
}

.fv-prose {
  font-size: 15px;
  line-height: 1.75;
  color: var(--fv-text-soft);
}

.fv-prose p + p {
  margin-top: 1em;
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

.fv-confidence-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  letter-spacing: 0.02em;
}

/* Dashboard project cards */
.fv-project-card {
  display: flex;
  flex-direction: column;
  background: var(--fv-surface-2);
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-lg);
  padding: 20px;
  min-height: 200px;
  text-align: left;
  transition: border-color 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.2s ease;
}

.fv-project-card-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
  margin-bottom: 4px;
}

.fv-project-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 10px 8px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--fv-bg) 55%, transparent);
  border: 1px solid var(--fv-border);
}

.fv-project-stat-icon {
  width: 14px;
  height: 14px;
  color: var(--fv-text-dim);
  margin-bottom: 2px;
}

.fv-project-stat-value {
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.1;
  color: var(--fv-text);
  font-variant-numeric: tabular-nums;
}

.fv-project-stat-label {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fv-text-dim);
}

.fv-project-metrics-locked {
  margin-top: 16px;
  margin-bottom: 4px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px dashed color-mix(in srgb, var(--fv-accent) 35%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-accent) 6%, var(--fv-bg));
}

.fv-project-metrics-locked-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.fv-project-metrics-locked-icon-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 10px;
  background: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  color: var(--fv-accent);
}

.fv-project-metrics-locked-badge {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 12px;
  height: 12px;
  padding: 1px;
  border-radius: 999px;
  background: var(--fv-surface-2);
  color: var(--fv-text-muted);
}

.fv-project-metrics-locked-cost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fv-text-soft);
}

.fv-project-stage-hint {
  margin-top: 14px;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--fv-accent);
}

.fv-project-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--fv-border);
}

.fv-project-card:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 35%, transparent);
  transform: translateY(-2px);
  box-shadow: 0 12px 40px -8px rgba(0, 0, 0, 0.5);
}

.fv-project-card-add {
  display: flex;
  align-items: center;
  justify-content: center;
  border-style: dashed;
  border-color: var(--fv-border-strong);
  min-height: 200px;
  cursor: pointer;
}

.fv-project-card-add:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 40%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 4%, transparent);
}

/* Marketing hero */
.fv-hero-glow {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 50% at 50% -10%, rgba(79, 107, 255, 0.18), transparent 55%),
    radial-gradient(ellipse 40% 30% at 80% 20%, rgba(124, 92, 255, 0.1), transparent 50%);
}
```

## 2. Refine flow — full surface

### `app/(dashboard)/new/page.tsx`

```typescript
import { RefineStagePanel } from "@/components/refinement/RefineStagePanel";

export default function NewExperimentPage() {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <RefineStagePanel />
    </div>
  );
}
```

### `components/refinement/RefineStagePanel.tsx`

```typescript
"use client";

import { ChatInterface } from "@/components/chat/ChatInterface";

interface RefineStagePanelProps {
  experimentId?: string;
  onExperimentChange?: () => void;
  onRefinementFinalized?: (finalized: boolean) => void;
}

/** Refine tab — chat-based idea refinement and validation. */
export function RefineStagePanel({
  experimentId,
  onExperimentChange,
  onRefinementFinalized,
}: RefineStagePanelProps) {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]">
      <ChatInterface
        experimentId={experimentId}
        onExperimentChange={onExperimentChange}
        onRefinementFinalized={onRefinementFinalized}
      />
    </div>
  );
}
```

### `components/chat/ChatInterface.tsx`

```typescript
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  chatTurn,
  confirmExperiment,
  editChatMessage,
  getExperiment,
  getExperimentChatMessages,
  ApiError,
} from "@/lib/api";
import type { ChatMessage as ChatMessageType, ChatTurnKind, ClarifyingQuestion, ClarifyingQuestionAnswer } from "@/lib/types";
import { FileText } from "lucide-react";
import { InlineResearchProgress } from "@/components/research/InlineResearchProgress";
import { ReportCanvas } from "@/components/research/ReportCanvas";
import { ClarifyingQuestionBlock } from "@/components/refinement/ClarifyingQuestionBlock";
import { ClarifyingQuestionsLoading } from "@/components/refinement/ClarifyingQuestionsLoading";
import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
import { PressureTestSection } from "@/components/refinement/PressureTestSection";
import {
  findPendingQuestionBlock,
  formatClarifyingAnswers,
} from "@/lib/clarifying-questions";
import {
  collectSourcedClarityBlocks,
  parseClarifyingAnswerContent,
} from "@/lib/refinement-thread";
import { ChatInput } from "./ChatInput";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { shouldShowValidationResearchPrompt } from "@/lib/validation-flow";
import { useValidationPaywallGate } from "@/components/wallet/useValidationPaywallGate";
import { ValidationResearchPrompt } from "@/components/wallet/ValidationResearchPrompt";
import { VALIDATION_PAYWALL_CREDITS } from "@/lib/wallet-paywall";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import { useWallet } from "@/lib/wallet-context";

const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

const DEEP_RESEARCH_LOCKED_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
  "RESEARCH_READY",
  "RESEARCH_FAILED",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "ANALYZING",
  "COMPLETED",
  "ARCHIVED",
]);

function isResearchUnderway(
  pipelineDispatched: boolean,
  experimentStatus: string | null,
): boolean {
  if (pipelineDispatched) return true;
  return (
    experimentStatus !== null &&
    RESEARCH_ACTIVE_STATUSES.has(experimentStatus)
  );
}

function isDeepResearchLocked(status: string | null): boolean {
  return status !== null && DEEP_RESEARCH_LOCKED_STATUSES.has(status);
}

function isResearchTriggeredStatus(status: string | null): boolean {
  if (status === null) return false;
  return isDeepResearchLocked(status);
}

const STARTER_PROMPTS = [
  "A tool that helps remote teams run async standups",
  "An app that matches dog owners for local group walks",
  "A marketplace for freelance CFOs serving startups",
  "A browser extension that summarizes Slack threads",
] as const;

const SCROLL_NEAR_BOTTOM_THRESHOLD_PX = 100;
const CHAT_TURN_TIMEOUT_MS = 120_000;

function mapApiMessages(
  messages: {
    id: string;
    role: ChatMessageType["role"];
    content: string;
    created_at: string;
    turn_kind?: ChatTurnKind | null;
    clarifying_questions?: ClarifyingQuestion[] | null;
  }[],
): ChatMessageType[] {
  return messages.map((msg) => ({
    id: msg.id,
    role: msg.role,
    content: msg.content,
    timestamp: msg.created_at,
    turnKind: msg.turn_kind ?? undefined,
    clarifyingQuestions: msg.clarifying_questions ?? undefined,
  }));
}

function isPersistedMessageId(id: string): boolean {
  return !id.startsWith("local-");
}

function formatReportDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(iso));
}

function apiErrorMessage(err: ApiError): string {
  if (err.status === 429) {
    const retry = err.retryAfterSeconds;
    return retry
      ? `Too many requests. Try again in ${retry} seconds.`
      : "Too many requests. Please wait a moment and try again.";
  }
  if (err.status === 402) {
    return (
      readPaidActionError(err, {
        fallbackRequired: VALIDATION_PAYWALL_CREDITS,
        fallback:
          "Not enough credits to start validation. Open your wallet to buy more.",
      })
    );
  }
  if (err.status === 409) {
    return "This experiment is archived or unavailable for chat.";
  }
  if (err.status === 404) {
    if (process.env.NODE_ENV === "development") {
      return "Chat is not available. Set AUTO_FIRE_CHAT_ENABLED=shadow (or on) in backend/.env and restart the API.";
    }
    return "Chat is not available right now. Please try again later.";
  }
  if (err.status === 502) {
    return readPaidActionError(err);
  }
  return "Something went wrong. Please try again.";
}

export interface ChatInterfaceProps {
  experimentId?: string;
  onExperimentChange?: () => void;
  onRefinementFinalized?: (finalized: boolean) => void;
}

export function ChatInterface({
  experimentId,
  onExperimentChange,
  onRefinementFinalized,
}: ChatInterfaceProps = {}) {
  const router = useRouter();
  const { requestValidation, paywallModal } = useValidationPaywallGate();
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [resolvedExperimentId, setResolvedExperimentId] = useState<string | null>(
    experimentId ?? null,
  );
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(Boolean(experimentId));
  const [researchStarted, setResearchStarted] = useState(false);
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [hasValidationReport, setHasValidationReport] = useState(false);
  const [reportReadyAt, setReportReadyAt] = useState<string | null>(null);
  const [prefillText, setPrefillText] = useState<string | null>(null);
  const [prefillNonce, setPrefillNonce] = useState(0);
  const [projectName, setProjectName] = useState("");
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const forceScrollRef = useRef(false);
  const messageIdCounter = useRef(0);

  const nextMessageId = useCallback(() => {
    messageIdCounter.current += 1;
    return `local-${messageIdCounter.current}`;
  }, []);

  const updateNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      isNearBottomRef.current = true;
      return;
    }
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    isNearBottomRef.current =
      distanceFromBottom <= SCROLL_NEAR_BOTTOM_THRESHOLD_PX;
  }, []);

  const handleScroll = useCallback(() => {
    updateNearBottom();
  }, [updateNearBottom]);

  useEffect(() => {
    if (forceScrollRef.current || isNearBottomRef.current) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
      forceScrollRef.current = false;
    }
  }, [messages, loading, researchStarted, hasValidationReport]);

  useEffect(() => {
    if (!experimentId) {
      setHistoryLoading(false);
      return;
    }

    let cancelled = false;

    async function loadExperimentChat() {
      setHistoryLoading(true);
      try {
        const [experiment, chatData] = await Promise.all([
          getExperiment(experimentId!),
          getExperimentChatMessages(experimentId!),
        ]);

        if (cancelled) return;

        setResolvedExperimentId(experimentId!);
        setExperimentStatus(experiment.status);
        if (experiment.name?.trim()) {
          setProjectName(experiment.name.trim());
        }
        const reportAvailable = experiment.validation_report != null;
        setHasValidationReport(reportAvailable);
        if (reportAvailable) {
          const lastMessage = chatData.messages.at(-1);
          setReportReadyAt(
            lastMessage?.created_at ?? new Date().toISOString(),
          );
        }

        if (isResearchTriggeredStatus(experiment.status)) {
          setResearchStarted(true);
        } else if (experiment.status === "REFINED") {
          setResearchStarted(false);
        }

        if (chatData.thread_id) {
          setThreadId(chatData.thread_id);
        }

        setMessages(mapApiMessages(chatData.messages));

        const finalized = chatData.messages.some(
          (m) => m.turn_kind === "refinement_finalize",
        );
        if (finalized) {
          onRefinementFinalized?.(true);
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    void loadExperimentChat();

    return () => {
      cancelled = true;
    };
  }, [experimentId, onRefinementFinalized]);

  useEffect(() => {
    const activeExperimentId = resolvedExperimentId;
    if (!activeExperimentId || !researchStarted) {
      if (!experimentId) {
        setHasValidationReport(false);
      }
      return;
    }

    let cancelled = false;

    async function loadExperiment() {
      if (!activeExperimentId) return;
      try {
        const data = await getExperiment(activeExperimentId);
        if (!cancelled) {
          setExperimentStatus(data.status);
          const reportAvailable = data.validation_report != null;
          if (reportAvailable) {
            setHasValidationReport(true);
            setReportReadyAt((prev) => prev ?? new Date().toISOString());
          } else {
            setHasValidationReport(false);
          }
        }
      } catch {
        // Ignore — progress polling handles transient errors elsewhere
      }
    }

    void loadExperiment();
    const intervalId = setInterval(loadExperiment, 3000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [resolvedExperimentId, researchStarted, experimentId]);

  function handleStarterChipClick(text: string) {
    setPrefillText(text);
    setPrefillNonce((n) => n + 1);
  }

  const refreshChatMessages = useCallback(async () => {
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;
    try {
      const chatData = await getExperimentChatMessages(expId);
      setMessages(mapApiMessages(chatData.messages));
      if (chatData.thread_id) {
        setThreadId(chatData.thread_id);
      }
    } catch {
      // Non-blocking — user can retry
    }
  }, [resolvedExperimentId, experimentId]);

  async function handleSend(
    text: string,
    deepResearch: boolean,
    attachments: Array<{ id: string; filename: string }> = [],
  ) {
    forceScrollRef.current = true;
    const attachmentLine =
      attachments.length > 0
        ? `\n\n📎 ${attachments.map((item) => item.filename).join(", ")}`
        : "";
    const userMessage: ChatMessageType = {
      id: nextMessageId(),
      role: "user",
      content: `${text || "Shared attachments"}${attachmentLine}`,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, CHAT_TURN_TIMEOUT_MS);

    try {
      const response = await chatTurn({
        message: text,
        deep_research: deepResearch,
        thread_id: threadId,
        experiment_id: resolvedExperimentId,
        idempotency_key: crypto.randomUUID(),
        name:
          !resolvedExperimentId && projectName.trim()
            ? projectName.trim()
            : undefined,
        attachment_ids: attachments.map((item) => item.id),
        signal: controller.signal,
      });

      const createdNewExperiment =
        !resolvedExperimentId && response.experiment_id != null;

      setThreadId(response.thread_id);
      if (response.experiment_id) {
        setResolvedExperimentId(response.experiment_id);
      }
      if (response.experiment_status) {
        setExperimentStatus(response.experiment_status);
      }

      const assistantMessage: ChatMessageType = {
        id: response.message_id,
        role: "assistant",
        content: response.assistant_message,
        timestamp: new Date().toISOString(),
        turnKind: response.turn_kind,
        clarifyingQuestions: response.clarifying_questions,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (
        response.turn_kind === "refinement_finalize" &&
        !response.pipeline_dispatched
      ) {
        setResearchStarted(false);
        setExperimentStatus(response.experiment_status ?? "REFINED");
      } else if (
        isResearchUnderway(
          response.pipeline_dispatched,
          response.experiment_status,
        )
      ) {
        setResearchStarted(true);
      }

      if (createdNewExperiment || response.turn_kind === "refinement_finalize") {
        notifyExperimentsChanged();
      }

      if (response.turn_kind === "refinement_finalize") {
        onRefinementFinalized?.(true);
      }

      if (createdNewExperiment && response.experiment_id && !experimentId) {
        router.replace(`/experiment/${response.experiment_id}`);
        return;
      }

      if (response.experiment_id && response.turn_kind === "refinement_finalize") {
        try {
          const exp = await getExperiment(response.experiment_id);
          if (exp.name?.trim()) {
            setProjectName(exp.name.trim());
          }
        } catch {
          // Non-blocking — sidebar still refreshes via event
        }
      }
    } catch (err) {
      const message = timedOut
        ? "This is taking longer than expected. Try refreshing — your answer may already be saved."
        : err instanceof ApiError
          ? apiErrorMessage(err)
          : "Something went wrong. Please try again.";

      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: "assistant",
          content: message,
          timestamp: new Date().toISOString(),
        },
      ]);

      if (timedOut) {
        void refreshChatMessages();
      }
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  async function handleStartValidation() {
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;

    const runConfirm = async () => {
      setLoading(true);
      try {
        const result = await confirmExperiment(expId);
        await syncWalletAfterPaidAction(
          refreshWallet,
          applyWalletPatch,
          result.credits_balance,
        );
        setResearchStarted(true);
        setExperimentStatus("RESEARCHING");
        notifyExperimentsChanged();
        onExperimentChange?.();
      } catch (err) {
        if (err instanceof ApiError && err.status === 502) {
          await refreshWallet();
        }
        const message =
          err instanceof ApiError
            ? apiErrorMessage(err)
            : "Could not start validation. Please try again.";
        setMessages((prev) => [
          ...prev,
          {
            id: nextMessageId(),
            role: "assistant",
            content: message,
            timestamp: new Date().toISOString(),
          },
        ]);
        throw err;
      } finally {
        setLoading(false);
      }
    };

    requestValidation(async () => {
      await runConfirm();
    });
  }

  async function handleEditMessage(messageId: string, newContent: string) {
    if (!threadId) return;

    const editIndex = messages.findIndex((msg) => msg.id === messageId);
    if (editIndex === -1) return;

    forceScrollRef.current = true;
    setMessages((prev) =>
      prev
        .slice(0, editIndex + 1)
        .map((msg, idx) =>
          idx === editIndex ? { ...msg, content: newContent } : msg,
        ),
    );
    setLoading(true);

    try {
      const response = await editChatMessage(threadId, messageId, newContent);

      setThreadId(response.thread_id);
      if (response.experiment_id) {
        setResolvedExperimentId(response.experiment_id);
      }
      if (response.experiment_status) {
        setExperimentStatus(response.experiment_status);
      }

      setMessages(mapApiMessages(response.messages));

      if (
        isResearchUnderway(
          response.pipeline_dispatched,
          response.experiment_status,
        )
      ) {
        setResearchStarted(true);
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? apiErrorMessage(err)
          : "Something went wrong. Please try again.";

      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: "assistant",
          content: message,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const chatDisabled =
    loading || historyLoading || experimentStatus === "ARCHIVED";
  const pendingQuestionBlock = useMemo(
    () => findPendingQuestionBlock(messages),
    [messages],
  );
  const firstUserMessageId = useMemo(
    () => messages.find((m) => m.role === "user")?.id,
    [messages],
  );
  const originalIdea = useMemo(
    () => messages.find((m) => m.role === "user")?.content,
    [messages],
  );
  const allClarityBlocks = useMemo(
    () => collectSourcedClarityBlocks(messages, firstUserMessageId ?? null),
    [messages, firstUserMessageId],
  );
  const clarityContentKey = useMemo(
    () =>
      messages
        .filter(
          (m) =>
            m.role === "user" &&
            m.id !== firstUserMessageId &&
            parseClarifyingAnswerContent(m.content),
        )
        .map((m) => m.content)
        .join("\n---\n"),
    [messages, firstUserMessageId],
  );
  const clarityMessageContentById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const msg of messages) {
      if (
        msg.role === "user" &&
        msg.id !== firstUserMessageId &&
        parseClarifyingAnswerContent(msg.content)
      ) {
        map[msg.id] = msg.content;
      }
    }
    return map;
  }, [messages, firstUserMessageId]);
  const hasRefinementFinalize = useMemo(
    () => messages.some((m) => m.turnKind === "refinement_finalize"),
    [messages],
  );

  useEffect(() => {
    onRefinementFinalized?.(hasRefinementFinalize);
  }, [hasRefinementFinalize, onRefinementFinalized]);
  const awaitingRefinementAfterUser = useMemo(() => {
    if (hasRefinementFinalize) return false;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "user") return false;
    if (last.id === firstUserMessageId) {
      return allClarityBlocks.length === 0;
    }
    return parseClarifyingAnswerContent(last.content ?? "") !== null;
  }, [
    messages,
    firstUserMessageId,
    allClarityBlocks.length,
    hasRefinementFinalize,
  ]);
  const isRefinementStageActive = useMemo(() => {
    if (hasRefinementFinalize) return false;
    if (
      isDeepResearchLocked(experimentStatus) ||
      (researchStarted && allClarityBlocks.length > 0)
    ) {
      return false;
    }
    return true;
  }, [
    hasRefinementFinalize,
    experimentStatus,
    researchStarted,
    allClarityBlocks.length,
  ]);
  const showQuestionBlock =
    pendingQuestionBlock !== null &&
    !loading &&
    isRefinementStageActive;
  const isQuestionsLoading =
    loading && !researchStarted && awaitingRefinementAfterUser;
  const awaitingServerReply =
    awaitingRefinementAfterUser &&
    !loading &&
    !showQuestionBlock &&
    isRefinementStageActive;
  const showQuestionsLoadingUi = isQuestionsLoading || awaitingServerReply;
  const showPressureTestSummary = useMemo(() => {
    if (allClarityBlocks.length === 0) return false;
    if (showQuestionBlock || showQuestionsLoadingUi) return false;
    if (hasRefinementFinalize) return true;
    if (researchStarted || isDeepResearchLocked(experimentStatus)) return true;
    return !awaitingRefinementAfterUser;
  }, [
    allClarityBlocks.length,
    showQuestionBlock,
    showQuestionsLoadingUi,
    hasRefinementFinalize,
    researchStarted,
    experimentStatus,
    awaitingRefinementAfterUser,
  ]);
  const inputDisabled = chatDisabled || showQuestionBlock;
  const showChatLoading = loading && !isQuestionsLoading;

  useEffect(() => {
    if (!awaitingServerReply) return;
    const expId = resolvedExperimentId ?? experimentId;
    if (!expId) return;

    let cancelled = false;

    async function poll() {
      if (cancelled) return;
      await refreshChatMessages();
    }

    void poll();
    const intervalId = window.setInterval(() => void poll(), 4000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [awaitingServerReply, resolvedExperimentId, experimentId, refreshChatMessages]);

  function handleQuestionSubmit(answers: ClarifyingQuestionAnswer[]) {
    if (!pendingQuestionBlock) return;
    const text = formatClarifyingAnswers(
      pendingQuestionBlock.questions,
      answers,
    );
    void handleSend(text, true);
  }

  const deepResearchLocked =
    researchStarted || isDeepResearchLocked(experimentStatus);
  const showValidationPrompt = shouldShowValidationResearchPrompt(
    hasRefinementFinalize,
    researchStarted,
    experimentStatus,
    hasValidationReport,
  );
  const showEmptyState =
    messages.length === 0 && !loading && !historyLoading && !experimentId;

  const showChatInput = useMemo(() => {
    const isIdeaIntake =
      messages.length === 0 &&
      !historyLoading &&
      !experimentId &&
      !resolvedExperimentId;
    if (isIdeaIntake) return true;
    return hasValidationReport;
  }, [
    messages.length,
    historyLoading,
    experimentId,
    resolvedExperimentId,
    hasValidationReport,
  ]);

  const openCanvas = useCallback(() => {
    setCanvasOpen(true);
  }, []);

  const handleResearchComplete = useCallback(() => {
    setHasValidationReport(true);
    setReportReadyAt((prev) => prev ?? new Date().toISOString());
    setExperimentStatus("RESEARCH_READY");
    notifyExperimentsChanged();
    onExperimentChange?.();
  }, [onExperimentChange]);

  return (
    <div className="flex h-full min-h-0 w-full flex-1 overflow-hidden">
      <div
        className={`flex h-full min-h-0 flex-col overflow-hidden bg-[var(--fv-bg)] ${
          canvasOpen
            ? "hidden w-full lg:flex lg:min-w-[320px] lg:max-w-[45%] lg:shrink-0 lg:w-[40%]"
            : "w-full flex-1"
        }`}
        style={{ transition: "width 350ms cubic-bezier(0.16, 1, 0.3, 1)" }}
      >
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="min-h-0 flex-1 overflow-y-auto px-4 py-6 lg:px-12 lg:py-8"
        >
          <div className="mx-auto w-full">
            {showEmptyState && (
              <div className="flex flex-col items-center py-16 text-center">
                <FivvleLogo size={40} className="mb-4" />
                <h2 className="text-lg font-semibold text-[var(--fv-text)]">
                  What&apos;s your idea?
                </h2>
                <p className="mt-2 max-w-md text-sm text-[var(--fv-text-muted)]">
                  Describe the problem you want to solve, who it&apos;s for, and
                  your proposed solution. Fivvle will refine it through a short
                  conversation, then kick off market research.
                </p>
                <div className="mt-6 flex max-w-lg flex-wrap justify-center gap-2">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleStarterChipClick(prompt)}
                      className="cursor-pointer rounded-full border border-white/[0.1] bg-white/[0.03] px-4 py-2 text-[13px] text-fv-text-soft transition-all duration-200 hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {historyLoading && messages.length === 0 && (
              <div className="flex justify-center py-16">
                <p className="text-sm text-[var(--fv-text-muted)]">
                  Loading conversation…
                </p>
              </div>
            )}

            {(() => {
              const hasThread =
                messages.length > 0 ||
                showQuestionBlock ||
                showQuestionsLoadingUi;
              let pressureTestRendered = false;

              const threadMessages = messages.map((msg, index) => {
                if (
                  msg.role === "assistant" &&
                  msg.turnKind === "refinement_clarify" &&
                  msg.clarifyingQuestions?.length
                ) {
                  return null;
                }

                const isSparkIdea =
                  msg.role === "user" && msg.id === firstUserMessageId;
                const isClarityAnswer =
                  msg.role === "user" &&
                  !isSparkIdea &&
                  parseClarifyingAnswerContent(msg.content);

                if (isClarityAnswer) {
                  if (pressureTestRendered || !showPressureTestSummary) return null;
                  pressureTestRendered = true;
                  return (
                    <PressureTestSection
                      key="pressure-test-unified"
                      blocks={allClarityBlocks}
                      contentKey={clarityContentKey}
                      messageContentById={clarityMessageContentById}
                      canEditMessage={(messageId) =>
                        !inputDisabled &&
                        !!threadId &&
                        isPersistedMessageId(messageId)
                      }
                      onEdit={handleEditMessage}
                    />
                  );
                }

                if (msg.turnKind === "refinement_finalize") {
                  return (
                    <div key={msg.id}>
                      <RefinementThreadMessage
                        id={msg.id}
                        role={msg.role}
                        content={msg.content}
                        turnKind={msg.turnKind}
                        isSparkIdea={isSparkIdea}
                        originalIdea={originalIdea}
                        canEdit={
                          msg.role === "user" &&
                          !inputDisabled &&
                          !!threadId &&
                          isPersistedMessageId(msg.id)
                        }
                        onEdit={handleEditMessage}
                        showRefining={false}
                      />
                      {showValidationPrompt ? (
                        <ValidationResearchPrompt
                          onStart={() => void handleStartValidation()}
                          loading={loading}
                        />
                      ) : null}
                    </div>
                  );
                }

                return (
                  <RefinementThreadMessage
                    key={msg.id}
                    id={msg.id}
                    role={msg.role}
                    content={msg.content}
                    turnKind={msg.turnKind}
                    isSparkIdea={isSparkIdea}
                    originalIdea={originalIdea}
                    canEdit={
                      msg.role === "user" &&
                      !inputDisabled &&
                      !!threadId &&
                      isPersistedMessageId(msg.id)
                    }
                    onEdit={handleEditMessage}
                    showRefining={
                      msg.role === "assistant" &&
                      !researchStarted &&
                      !deepResearchLocked &&
                      index === messages.length - 1 &&
                      !loading &&
                      !showQuestionBlock
                    }
                  />
                );
              });

              if (!hasThread) return null;

              return (
                <article className="ra-story">
                  {threadMessages}
                  {showPressureTestSummary && !pressureTestRendered && (
                    <PressureTestSection
                      key="pressure-test-unified"
                      blocks={allClarityBlocks}
                      contentKey={clarityContentKey}
                      messageContentById={clarityMessageContentById}
                      canEditMessage={(messageId) =>
                        !inputDisabled &&
                        !!threadId &&
                        isPersistedMessageId(messageId)
                      }
                      onEdit={handleEditMessage}
                    />
                  )}
                  {showQuestionBlock && pendingQuestionBlock && (
                    <ClarifyingQuestionBlock
                      variant="ascent"
                      questions={pendingQuestionBlock.questions}
                      questionNumberStart={allClarityBlocks.length + 1}
                      submitting={loading}
                      onSubmit={(answers) => void handleQuestionSubmit(answers)}
                    />
                  )}
                  {showQuestionsLoadingUi && (
                    <ClarifyingQuestionsLoading
                      questionNumber={allClarityBlocks.length + 1}
                      phase={isQuestionsLoading ? "submitting" : "syncing"}
                      onRetry={() => void refreshChatMessages()}
                    />
                  )}
                </article>
              );
            })()}

            {showChatLoading && (
              <div className="fv-msg-enter border-b border-[var(--fv-border)] py-6">
                <div className="mx-auto w-full max-w-full lg:max-w-[680px]">
                  <div className="flex items-start gap-3">
                    <FivvleLogo size={24} />
                    <div className="min-w-0 flex-1">
                      <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
                        Fivvle
                      </span>
                      <div className="flex items-center gap-1.5 py-1">
                        {[0, 150, 300].map((delay) => (
                          <span
                            key={delay}
                            className="h-2 w-2 animate-pulse rounded-full bg-[var(--fv-text-dim)]"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {researchStarted && resolvedExperimentId && (
              <InlineResearchProgress
                experimentId={resolvedExperimentId}
                reportReady={hasValidationReport}
                onComplete={handleResearchComplete}
              />
            )}

            {hasValidationReport && resolvedExperimentId && (
              <div className="mx-auto my-6 w-full max-w-full lg:max-w-[680px]">
                <button
                  type="button"
                  onClick={openCanvas}
                  className="group w-full rounded-xl border border-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)] bg-gradient-to-br from-[color-mix(in_srgb,var(--fv-accent)_10%,transparent)] to-transparent p-5 text-left transition-all hover:border-[var(--fv-accent)]/50"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--fv-accent-muted)]">
                      <FileText className="h-6 w-6 text-[var(--fv-accent)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-[var(--fv-text)]">
                        Validation report ready
                      </p>
                      <p className="mt-0.5 text-sm text-[var(--fv-text-muted)]">
                        {reportReadyAt
                          ? formatReportDate(reportReadyAt)
                          : "View your market research findings"}
                      </p>
                    </div>
                    <span className="fv-btn-primary shrink-0 px-4 py-2 text-sm opacity-90 group-hover:opacity-100">
                      Open report
                    </span>
                  </div>
                </button>
              </div>
            )}

            <div ref={scrollAnchorRef} />
          </div>
        </div>

        {!experimentId && !resolvedExperimentId && showChatInput && (
          <div className="shrink-0 border-t border-[var(--fv-border)] bg-[var(--fv-surface)]/50 px-4 py-3 lg:px-12">
            <label
              htmlFor="project-name"
              className="mb-1.5 block text-[12px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]"
            >
              Project name{" "}
              <span className="normal-case text-[var(--fv-text-dim)]">
                (optional — AI will suggest one if blank)
              </span>
            </label>
            <input
              id="project-name"
              type="text"
              value={projectName}
              maxLength={100}
              disabled={inputDisabled}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Async Standup, CFO Match"
              className="fv-input w-full max-w-md px-3 py-2 text-sm"
            />
          </div>
        )}

        {showChatInput && (
          <ChatInput
            onSend={handleSend}
            disabled={inputDisabled}
            deepResearchLocked={deepResearchLocked}
            prefillText={prefillText}
            prefillNonce={prefillNonce}
            placeholder={
              hasValidationReport
                ? "Continue the conversation…"
                : "Describe your idea..."
            }
          />
        )}
      </div>

      {canvasOpen && resolvedExperimentId && (
        <div className="fixed inset-0 z-[60] flex min-h-0 flex-col overflow-hidden border-l border-[var(--fv-border)] bg-[var(--fv-bg)] fv-msg-enter lg:relative lg:z-auto lg:min-h-0 lg:flex lg:min-w-0 lg:flex-1 lg:overflow-hidden">
          <ReportCanvas
            experimentId={resolvedExperimentId}
            projectName={projectName || "Validation report"}
            onClose={() => setCanvasOpen(false)}
            mobile
          />
        </div>
      )}
      {paywallModal}
    </div>
  );
}
```

### `components/chat/ChatMessage.tsx`

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import type { ChatRole } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { getChatUserLabel } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import { ChatMarkdown } from "./ChatMarkdown";

interface ChatMessageProps {
  id: string;
  role: ChatRole;
  content: string;
  timestamp?: string;
  showRefining?: boolean;
  canEdit?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<void>;
}

export function ChatMessage({
  id,
  role,
  content,
  showRefining = false,
  canEdit = false,
  onEdit,
}: ChatMessageProps) {
  const { user } = useAuth();
  const isUser = role === "user";
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isEditing) {
      setDraft(content);
    }
  }, [content, isEditing]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(
        textareaRef.current.value.length,
        textareaRef.current.value.length,
      );
    }
  }, [isEditing]);

  function handleCancel() {
    setDraft(content);
    setIsEditing(false);
  }

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed || !onEdit || trimmed === content) {
      handleCancel();
      return;
    }
    setSaving(true);
    try {
      await onEdit(id, trimmed);
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fv-msg-enter group border-b border-[var(--fv-border)] py-6">
      <div className="relative mx-auto w-full max-w-full lg:max-w-[680px]">
        {isUser && canEdit && !isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            aria-label="Edit message"
            className="absolute right-0 top-0 rounded-md p-1.5 text-[var(--fv-text-muted)] opacity-0 transition-opacity hover:bg-white/[0.06] hover:text-[var(--fv-text-soft)] group-hover:opacity-100"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
        <div className="flex items-start gap-3">
          {isUser ? (
            <UserAvatar
              displayName={user?.displayName}
              email={user?.email}
              photoUrl={user?.photoURL}
              size="sm"
              className="!h-6 !w-6 !text-[11px]"
            />
          ) : (
            <FivvleLogo size={24} />
          )}
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              {isUser ? getChatUserLabel(user) : "Fivvle"}
              {!isUser && showRefining && (
                <span className="fv-refining-badge ml-2">Refining</span>
              )}
            </span>
            {isEditing ? (
              <div className="space-y-3">
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={saving}
                  rows={3}
                  className="fv-input w-full resize-y px-3 py-2 text-[15px] leading-[1.65] text-[var(--fv-text)]"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={saving || !draft.trim()}
                    className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={saving}
                    className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : isUser ? (
              <div className="fv-msg-user whitespace-pre-wrap break-words">
                {content}
              </div>
            ) : (
              <ChatMarkdown content={content} className="fv-msg-ai break-words" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

### `components/chat/ChatInput.tsx`

```typescript
"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import { Image as ImageIcon, Loader2, Paperclip, Send, X, Zap } from "lucide-react";
import { uploadChatAttachments, ApiError } from "@/lib/api";
import type { ChatAttachmentUploadItem } from "@/lib/api";

const MAX_ATTACHMENTS = 5;

const ACCEPTED_FILE_TYPES =
  "image/png,image/jpeg,image/webp,.pdf,.txt,.md,.markdown,.docx";

interface PendingAttachment extends ChatAttachmentUploadItem {
  localKey: string;
}

interface ChatInputProps {
  onSend: (
    text: string,
    deepResearch: boolean,
    attachments: Array<{ id: string; filename: string }>,
  ) => void;
  disabled: boolean;
  placeholder: string;
  deepResearchLocked?: boolean;
  prefillText?: string | null;
  prefillNonce?: number;
}

const MIN_TEXTAREA_HEIGHT_PX = 40;
const MAX_TEXTAREA_HEIGHT_PX = 120;

function getMaxTextareaHeightPx(): number {
  if (typeof window === "undefined") return MAX_TEXTAREA_HEIGHT_PX;
  const mobileCap = Math.floor(window.innerHeight * 0.28);
  if (window.matchMedia("(max-width: 1023px)").matches) {
    return Math.min(MAX_TEXTAREA_HEIGHT_PX, mobileCap);
  }
  return MAX_TEXTAREA_HEIGHT_PX;
}

function uploadErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (typeof err.body === "object" && err.body !== null && "detail" in err.body) {
      const detail = (err.body as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  }
  return "Could not upload file. Try a smaller PNG, JPEG, WebP, PDF, TXT, Markdown, or DOCX.";
}

function extensionForImageMime(mime: string): string {
  if (mime === "image/png") return "png";
  if (mime === "image/webp") return "webp";
  return "jpg";
}

function filesFromClipboardItems(items: DataTransferItemList): File[] {
  const imageFiles: File[] = [];
  for (const item of Array.from(items)) {
    if (!item.type.startsWith("image/")) continue;
    const blob = item.getAsFile();
    if (!blob) continue;
    const ext = extensionForImageMime(item.type);
    imageFiles.push(
      new File([blob], `pasted-image-${Date.now()}-${imageFiles.length}.${ext}`, {
        type: item.type,
      }),
    );
  }
  return imageFiles;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder,
  deepResearchLocked = false,
  prefillText = null,
  prefillNonce = 0,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [deepResearch, setDeepResearch] = useState(true);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [uploadingCount, setUploadingCount] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const nextHeight = Math.max(
      MIN_TEXTAREA_HEIGHT_PX,
      Math.min(el.scrollHeight, getMaxTextareaHeightPx()),
    );
    el.style.height = `${nextHeight}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [resizeTextarea]);

  useEffect(() => {
    const onResize = () => resizeTextarea();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [resizeTextarea]);

  useEffect(() => {
    if (!prefillText || prefillNonce === 0) return;
    const el = textareaRef.current;
    if (!el) return;
    el.value = prefillText;
    resizeTextarea();
    el.focus();
  }, [prefillText, prefillNonce, resizeTextarea]);

  const isBusy = disabled || uploadingCount > 0;

  function handleSend() {
    const el = textareaRef.current;
    if (!el || isBusy) return;
    const text = el.value.trim();
    if (!text && attachments.length === 0) return;
    onSend(
      text,
      deepResearchLocked ? false : deepResearch,
      attachments.map((item) => ({ id: item.id, filename: item.filename })),
    );
    el.value = "";
    el.style.height = `${MIN_TEXTAREA_HEIGHT_PX}px`;
    setAttachments([]);
    setUploadError(null);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function uploadFiles(selected: File[]) {
    if (selected.length === 0) return;

    const remainingSlots = MAX_ATTACHMENTS - attachments.length;
    if (remainingSlots <= 0) {
      setUploadError(`You can attach up to ${MAX_ATTACHMENTS} files per message.`);
      return;
    }

    const batch = selected.slice(0, remainingSlots);
    if (selected.length > remainingSlots) {
      setUploadError(`Only ${remainingSlots} more file(s) can be attached.`);
    } else {
      setUploadError(null);
    }

    setUploadingCount((count) => count + batch.length);
    try {
      const uploaded = await uploadChatAttachments(batch);
      setAttachments((prev) => [
        ...prev,
        ...uploaded.map((item, index) => ({
          ...item,
          localKey: `${item.id}-${Date.now()}-${index}`,
        })),
      ]);
    } catch (err) {
      setUploadError(uploadErrorMessage(err));
    } finally {
      setUploadingCount((count) => Math.max(0, count - batch.length));
    }
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    event.target.value = "";
    await uploadFiles(selected);
  }

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const items = event.clipboardData?.items;
    if (!items) return;

    const imageFiles = filesFromClipboardItems(items);
    if (imageFiles.length === 0) return;

    event.preventDefault();
    void uploadFiles(imageFiles);
  }

  function removeAttachment(localKey: string) {
    setAttachments((prev) => prev.filter((item) => item.localKey !== localKey));
    setUploadError(null);
  }

  return (
    <div className="shrink-0 bg-gradient-to-t from-[var(--fv-bg)] via-[var(--fv-bg)]/95 to-transparent px-4 pb-3 pt-2 backdrop-blur-md lg:px-12">
      <div className="mx-auto max-w-3xl rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)]/90 p-2 shadow-[0_-4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
        {(attachments.length > 0 || uploadError) && (
          <div className="mb-2 space-y-1.5 px-1">
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {attachments.map((item) => (
                  <span
                    key={item.localKey}
                    className="inline-flex max-w-full items-center gap-1 rounded-full border border-[var(--fv-border)] bg-[var(--fv-bg)]/70 px-2.5 py-1 text-[12px] text-[var(--fv-text-muted)]"
                    title={item.excerpt}
                  >
                    {item.content_kind === "image" ? (
                      <ImageIcon className="h-3 w-3 shrink-0" />
                    ) : (
                      <Paperclip className="h-3 w-3 shrink-0" />
                    )}
                    <span className="truncate">{item.filename}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(item.localKey)}
                      className="fv-icon-btn !h-5 !w-5 shrink-0"
                      aria-label={`Remove ${item.filename}`}
                      disabled={isBusy}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            {uploadError && (
              <p className="text-[12px] text-red-400">{uploadError}</p>
            )}
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            multiple
            accept={ACCEPTED_FILE_TYPES}
            onChange={handleFileChange}
          />
          <button
            type="button"
            className="fv-icon-btn mb-0.5 shrink-0 disabled:cursor-not-allowed disabled:opacity-40"
            title="Attach images, PDFs, or documents (or paste an image)"
            aria-label="Attach file"
            disabled={isBusy || attachments.length >= MAX_ATTACHMENTS}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploadingCount > 0 ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Paperclip className="h-4 w-4" />
            )}
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={placeholder}
            disabled={isBusy}
            onChange={resizeTextarea}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            className="max-h-[120px] min-h-[40px] flex-1 resize-none border-none bg-transparent px-1 py-2 text-[14px] leading-5 text-[var(--fv-text)] outline-none placeholder:text-[var(--fv-text-muted)] disabled:cursor-not-allowed disabled:opacity-50"
          />

          <button
            type="button"
            onClick={handleSend}
            disabled={isBusy}
            aria-label="Send message"
            className="fv-send-btn mb-0.5 shrink-0 disabled:cursor-not-allowed"
          >
            {disabled ? (
              <Loader2 className="h-[15px] w-[15px] animate-spin" />
            ) : (
              <Send className="h-[15px] w-[15px]" />
            )}
          </button>
        </div>

        {!deepResearchLocked && (
          <div className="mt-1.5 flex items-center px-1">
            <button
              type="button"
              onClick={() => setDeepResearch((v) => !v)}
              disabled={isBusy}
              className={`fv-deep-toggle ${deepResearch ? "fv-deep-toggle-on" : ""}`}
            >
              <Zap className="h-[13px] w-[13px]" />
              Deep Research {deepResearch ? "ON" : "OFF"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

### `components/chat/ChatMarkdown.tsx`

```typescript
"use client";

import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const DISALLOWED_ELEMENTS = [
  "script",
  "style",
  "iframe",
  "object",
  "embed",
  "form",
  "input",
  "textarea",
  "button",
];

function isSafeHref(href: string | undefined): href is string {
  if (!href) return false;
  try {
    const url = new URL(href);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function SafeLink({
  href,
  children,
  ...props
}: ComponentPropsWithoutRef<"a">) {
  if (!isSafeHref(href)) {
    return <span>{children}</span>;
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  );
}

interface ChatMarkdownProps {
  content: string;
  className?: string;
}

export function ChatMarkdown({ content, className = "" }: ChatMarkdownProps) {
  return (
    <div className={`fv-chat-md ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        disallowedElements={DISALLOWED_ELEMENTS}
        unwrapDisallowed
        components={{
          a: SafeLink,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

### `components/refinement/ClarifyingQuestionBlock.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";
import {
  createEmptyAnswers,
  isQuestionAnswerValid,
} from "@/lib/clarifying-questions";
import "./refinement-ascent.css";
import "./refinement-thread.css";

interface ClarifyingQuestionBlockProps {
  questions: ClarifyingQuestion[];
  intro?: string;
  /** 1-based index for the first question in this batch (continues across rounds). */
  questionNumberStart?: number;
  submitting?: boolean;
  variant?: "default" | "ascent" | "peak";
  onSubmit: (answers: ClarifyingQuestionAnswer[]) => void;
}

export function ClarifyingQuestionBlock({
  questions,
  intro,
  questionNumberStart = 1,
  submitting = false,
  variant = "default",
  onSubmit,
}: ClarifyingQuestionBlockProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<ClarifyingQuestionAnswer[]>(() =>
    createEmptyAnswers(questions),
  );
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentIndex(0);
    setAnswers(createEmptyAnswers(questions));
    setValidationError(null);
  }, [questions]);

  const currentQuestion = questions[currentIndex];
  const currentAnswer = answers[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === questions.length - 1;

  function updateAnswer(next: ClarifyingQuestionAnswer) {
    setAnswers((prev) =>
      prev.map((item, idx) => (idx === currentIndex ? next : item)),
    );
    setValidationError(null);
  }

  function toggleOption(optionIndex: number) {
    const option = currentQuestion.options[optionIndex];
    const selected = new Set(currentAnswer.selectedOptions);
    if (selected.has(option)) {
      selected.delete(option);
    } else {
      selected.add(option);
    }
    updateAnswer({
      selectedOptions: [...selected],
      otherText: currentAnswer.otherText,
    });
  }

  function handlePrevious() {
    setValidationError(null);
    setCurrentIndex((idx) => Math.max(0, idx - 1));
  }

  function handleNext() {
    if (!isQuestionAnswerValid(currentAnswer)) {
      setValidationError(
        "Select at least one option (you can pick multiple) or enter a custom answer.",
      );
      return;
    }
    setValidationError(null);
    if (isLast) {
      onSubmit(answers);
      return;
    }
    setCurrentIndex((idx) => idx + 1);
  }

  const isAscent = variant === "ascent" || variant === "peak";
  const isPeak = variant === "peak";
  const isAscentLive = variant === "ascent";
  const globalQuestionNumber = questionNumberStart + currentIndex;

  return (
    <div
      className={`fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ${
        isAscentLive ? "ra-clarify-wrap" : ""
      }`}
    >
      <div
        className={
          isAscent
            ? isPeak
              ? "rt-clarify-panel"
              : "ra-clarify-panel"
            : "overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]"
        }
      >
        <div
          className={
            isAscent
              ? isPeak
                ? "rt-clarify-progress"
                : "ra-clarify-header"
              : "border-b border-[var(--fv-border)] px-6 py-4 text-center"
          }
        >
          {isAscent ? (
            isPeak ? (
              <>
                <p className="rt-clarify-progress-label">Sharpen your idea</p>
                <p className="rt-clarify-progress-count">
                  Question {currentIndex + 1} of {questions.length}
                </p>
              </>
            ) : (
              <>
                <h3 className="ra-clarify-title">Sharpen your idea</h3>
                <p className="ra-clarify-count">
                  Question {globalQuestionNumber}
                </p>
              </>
            )
          ) : (
            <p className="text-sm font-medium text-[var(--fv-text-muted)]">
              {currentIndex + 1} / {questions.length}
            </p>
          )}
        </div>

        <div className="space-y-6 px-6 py-6">
          {intro && currentIndex === 0 && !isAscentLive && (
            <p className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
              {intro}
            </p>
          )}

          <div>
            <h3 className="text-base font-semibold text-[var(--fv-text)]">
              {isAscentLive
                ? `${globalQuestionNumber}. ${currentQuestion.question}`
                : `Q${currentIndex + 1}. ${currentQuestion.question}`}
            </h3>
            <p className="mt-1.5 text-xs text-[var(--fv-text-muted)]">
              You can select multiple options — choose every answer that applies.
            </p>
          </div>

          <ol className="space-y-3">
            {currentQuestion.options.map((option, optionIndex) => {
              const selected = currentAnswer.selectedOptions.includes(option);

              return (
                <li key={`${currentIndex}-${optionIndex}`}>
                  <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--fv-border)] px-4 py-3 transition-colors hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5 has-[:checked]:border-[var(--fv-accent)]/50 has-[:checked]:bg-[var(--fv-accent)]/5">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={submitting}
                      onChange={() => toggleOption(optionIndex)}
                      className="mt-0.5 shrink-0 accent-[var(--fv-accent)]"
                    />
                    <span className="text-sm leading-relaxed text-[var(--fv-text)]">
                      <span className="mr-2 font-medium text-[var(--fv-text-muted)]">
                        {optionIndex + 1}.
                      </span>
                      {option}
                    </span>
                  </label>
                </li>
              );
            })}

            <li>
              <label className="flex flex-col gap-2 rounded-lg border border-[var(--fv-border)] px-4 py-3">
                <span className="text-sm font-medium text-[var(--fv-text)]">
                  {currentQuestion.options.length + 1}. Other:
                </span>
                <input
                  type="text"
                  value={currentAnswer.otherText}
                  disabled={submitting}
                  onChange={(e) =>
                    updateAnswer({
                      selectedOptions: currentAnswer.selectedOptions,
                      otherText: e.target.value,
                    })
                  }
                  placeholder="Type your answer…"
                  className="fv-input w-full px-3 py-2 text-sm"
                />
              </label>
            </li>
          </ol>

          {validationError && (
            <p className="text-sm text-[var(--fv-danger)]">{validationError}</p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-[var(--fv-border)] px-6 py-4">
          <button
            type="button"
            onClick={handlePrevious}
            disabled={isFirst || submitting}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={submitting}
            className="fv-btn-primary px-5 py-2 text-sm disabled:opacity-50"
          >
            {submitting ? "Submitting…" : isLast ? "Submit" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

### `components/refinement/ClarifyingQuestionsLoading.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import "./refinement-ascent.css";

interface ClarifyingQuestionsLoadingProps {
  questionNumber: number;
  phase?: "submitting" | "syncing";
  onRetry?: () => void;
}

/** Shown while waiting for the next clarifying question — not the chat typing indicator. */
export function ClarifyingQuestionsLoading({
  questionNumber,
  phase = "submitting",
  onRetry,
}: ClarifyingQuestionsLoadingProps) {
  const [showSlowHint, setShowSlowHint] = useState(false);

  useEffect(() => {
    setShowSlowHint(false);
    const timer = window.setTimeout(() => setShowSlowHint(true), 25_000);
    return () => window.clearTimeout(timer);
  }, [questionNumber, phase]);

  const statusLabel =
    phase === "syncing"
      ? "Checking for your next question…"
      : "Preparing your next question…";

  return (
    <div className="fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ra-clarify-wrap">
      <div className="ra-clarify-panel ra-clarify-panel-loading" aria-busy="true">
        <div className="ra-clarify-header">
          <h3 className="ra-clarify-title">Sharpen your idea</h3>
          <p className="ra-clarify-count">Question {questionNumber}</p>
        </div>

        <div className="ra-questions-loading-body">
          <div className="ra-questions-loading-skeleton" aria-hidden>
            <div className="ra-questions-loading-line ra-questions-loading-line-title" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option ra-questions-loading-option-short" />
          </div>

          <div className="ra-questions-loading-status">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
            <span>{statusLabel}</span>
          </div>

          {showSlowHint && (
            <div className="ra-questions-loading-slow">
              <p className="ra-questions-loading-slow-text">
                {phase === "syncing"
                  ? "Still waiting on Fivvle. You can refresh to pull the latest questions."
                  : "This is taking longer than usual. Fivvle is still working on your next question."}
              </p>
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="fv-btn-ghost px-3 py-1.5 text-sm"
                >
                  Refresh
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### `components/refinement/RefinementThreadMessage.tsx`

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Lightbulb,
  MessageCircleQuestion,
  Pencil,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { ChatRole, ChatTurnKind } from "@/lib/types";
import { useOptionalAuth } from "@/lib/auth-context";
import { getChatUserLabel } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import {
  excerptIdea,
  parseClarifyingAnswerContent,
  parseResearchingHypothesis,
} from "@/lib/refinement-thread";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import "./refinement-ascent.css";
import "./refinement-thread.css";

export type RefinementThreadVariant = "ascent" | "peak";

interface RefinementThreadMessageProps {
  id: string;
  role: ChatRole;
  content: string;
  turnKind?: ChatTurnKind | null;
  isSparkIdea?: boolean;
  originalIdea?: string;
  clarityRound?: number;
  /** Label when rendered outside AuthProvider (e.g. refinement demos). */
  demoUserLabel?: string;
  showRefining?: boolean;
  canEdit?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<void>;
  /** Ascent is live in Refine; peak kept for /refinement-demos comparison. */
  variant?: RefinementThreadVariant;
}

function EditActions({
  saving,
  canSave,
  onSave,
  onCancel,
}: {
  saving: boolean;
  canSave: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !canSave}
        className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
      >
        Cancel
      </button>
    </div>
  );
}

export function RefinementThreadMessage({
  id,
  role,
  content,
  turnKind,
  isSparkIdea = false,
  originalIdea,
  clarityRound = 1,
  demoUserLabel,
  showRefining = false,
  canEdit = false,
  onEdit,
  variant = "ascent",
}: RefinementThreadMessageProps) {
  const auth = useOptionalAuth();
  const user = auth?.user ?? null;
  const userLabel = user
    ? getChatUserLabel(user)
    : (demoUserLabel?.trim() || "You");
  const isUser = role === "user";
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const clarityBlocks = isUser ? parseClarifyingAnswerContent(content) : null;
  const refinedHypothesis =
    !isUser && turnKind === "refinement_finalize"
      ? parseResearchingHypothesis(content)
      : null;

  useEffect(() => {
    if (!isEditing) setDraft(content);
  }, [content, isEditing]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(
        textareaRef.current.value.length,
        textareaRef.current.value.length,
      );
    }
  }, [isEditing]);

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed || !onEdit || trimmed === content) {
      setDraft(content);
      setIsEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onEdit(id, trimmed);
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  }

  const editButton =
    isUser && canEdit && !isEditing ? (
      <button
        type="button"
        onClick={() => setIsEditing(true)}
        aria-label="Edit message"
        className="rounded-md p-1.5 text-[var(--fv-text-muted)] transition-colors hover:bg-white/[0.06] hover:text-[var(--fv-text-soft)]"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    ) : null;

  const isAscent = variant === "ascent";

  if (isSparkIdea && isUser) {
    if (isAscent) {
      return (
        <div className="fv-msg-enter">
          <header className="ra-hero">
            <div className="ra-hero-head">
              <div>
                <div className="ra-hero-icon" aria-hidden>
                  <Lightbulb />
                </div>
                <p className="ra-kicker">Chapter 1 · The spark</p>
                <h3 className="ra-hero-title">
                  Every great company starts as a sentence.
                </h3>
              </div>
              {editButton}
            </div>
            {isEditing ? (
              <>
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={saving}
                  rows={5}
                  className="fv-input mt-2 w-full resize-y px-3 py-2 text-[15px] leading-[1.65]"
                />
                <EditActions
                  saving={saving}
                  canSave={Boolean(draft.trim())}
                  onSave={() => void handleSave()}
                  onCancel={() => {
                    setDraft(content);
                    setIsEditing(false);
                  }}
                />
              </>
            ) : (
              <>
                <blockquote className="ra-hero-quote">{content}</blockquote>
                <div className="ra-hero-byline">
                  <UserAvatar
                    displayName={user?.displayName ?? demoUserLabel}
                    email={user?.email}
                    photoUrl={user?.photoURL}
                    size="sm"
                    className="!h-5 !w-5 !text-[10px]"
                  />
                  {userLabel}
                </div>
              </>
            )}
          </header>
        </div>
      );
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker" aria-hidden>
              <Lightbulb />
            </div>
            <div className="rt-card rt-card-spark">
              <div className="rt-card-head">
                <p className="rt-eyebrow rt-eyebrow-accent">Your starting point</p>
                <span className="rt-badge">
                  <Sparkles className="h-3 w-3" aria-hidden />
                  Raw idea
                </span>
              </div>
              <div className="rt-card-body">
                {isEditing ? (
                  <>
                    <textarea
                      ref={textareaRef}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      disabled={saving}
                      rows={5}
                      className="fv-input w-full resize-y px-3 py-2 text-[15px] leading-[1.65]"
                    />
                    <EditActions
                      saving={saving}
                      canSave={Boolean(draft.trim())}
                      onSave={() => void handleSave()}
                      onCancel={() => {
                        setDraft(content);
                        setIsEditing(false);
                      }}
                    />
                  </>
                ) : (
                  <>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <UserAvatar
                          displayName={user?.displayName ?? demoUserLabel}
                          email={user?.email}
                          photoUrl={user?.photoURL}
                          size="sm"
                          className="!h-6 !w-6 !text-[11px]"
                        />
                        <span className="text-[13px] font-medium text-[var(--fv-text-soft)]">
                          {userLabel}
                        </span>
                      </div>
                      {editButton}
                    </div>
                    <p className="rt-spark-text">{content}</p>
                  </>
                )}
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  if (clarityBlocks && isUser) {
    if (isAscent) {
      return null;
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker" aria-hidden>
              <MessageCircleQuestion />
            </div>
            <div className="rt-card">
              <div className="rt-card-head">
                <p className="rt-eyebrow rt-eyebrow-accent">
                  Clarity round {clarityRound}
                </p>
                {editButton}
              </div>
              <div className="rt-card-body">
                {isEditing ? (
                  <>
                    <textarea
                      ref={textareaRef}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      disabled={saving}
                      rows={8}
                      className="fv-input w-full resize-y px-3 py-2 font-mono text-[13px] leading-[1.55]"
                    />
                    <EditActions
                      saving={saving}
                      canSave={Boolean(draft.trim())}
                      onSave={() => void handleSave()}
                      onCancel={() => {
                        setDraft(content);
                        setIsEditing(false);
                      }}
                    />
                  </>
                ) : (
                  <div className="rt-clarity-stack">
                    {clarityBlocks.map((block) => (
                      <div key={block.question} className="rt-clarity-item">
                        <p className="rt-clarity-q">{block.question}</p>
                        <div className="rt-clarity-answers">
                          {block.answers.map((answer) => (
                            <span key={answer} className="rt-clarity-chip">
                              {answer}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  if (refinedHypothesis) {
    const before = originalIdea ? excerptIdea(originalIdea) : null;

    if (isAscent) {
      return (
        <div className="fv-msg-enter">
          <section className="ra-finale">
            <div className="ra-finale-badge">
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              Refined &amp; research-ready
            </div>
            <p className="ra-kicker ra-kicker-light">Chapter 3 · The upgrade</p>
            <div className="ra-finale-grid">
              {before ? (
                <div className="ra-finale-before">
                  <p className="ra-finale-label">Before</p>
                  <p>{before}</p>
                </div>
              ) : null}
              {before ? (
                <ArrowRight className="ra-finale-arrow" aria-hidden />
              ) : null}
              <div className="ra-finale-after">
                <p className="ra-finale-label">Researching</p>
                <p className="ra-finale-hypothesis">{refinedHypothesis}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker rt-step-marker-success" aria-hidden>
              <TrendingUp />
            </div>
            <div className="rt-card rt-card-refined">
              <div className="rt-card-head">
                <div className="flex items-center gap-2">
                  <FivvleLogo size={22} />
                  <p className="rt-eyebrow rt-eyebrow-success mb-0">
                    Refined hypothesis
                  </p>
                </div>
                <span className="rt-badge rt-badge-success">Upgrade ready</span>
              </div>
              <div className="rt-card-body">
                <div className="rt-upgrade-grid">
                  {before ? (
                    <div className="rt-upgrade-before">
                      <p className="rt-upgrade-label">Where you started</p>
                      <p className="rt-upgrade-text">{before}</p>
                    </div>
                  ) : null}
                  {before ? (
                    <div className="rt-upgrade-arrow" aria-hidden>
                      <ArrowUpRight />
                    </div>
                  ) : null}
                  <div className="rt-upgrade-after">
                    <p className="rt-upgrade-label">What we&apos;re researching</p>
                    <p className="rt-upgrade-text rt-upgrade-text-strong">
                      {refinedHypothesis}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  return (
    <div className="fv-msg-enter">
      <div
        className={`relative mx-auto w-full max-w-full lg:max-w-[720px] ${
          isAscent ? "ra-default-row" : "rt-default-row"
        }`}
      >
        <div className="flex items-start gap-3">
          {isUser ? (
            <UserAvatar
              displayName={user?.displayName ?? demoUserLabel}
              email={user?.email}
              photoUrl={user?.photoURL}
              size="sm"
              className="!h-6 !w-6 !text-[11px]"
            />
          ) : (
            <FivvleLogo size={24} />
          )}
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              {isUser ? userLabel : "Fivvle"}
              {!isUser && showRefining && (
                <span className="fv-refining-badge ml-2">Refining</span>
              )}
            </span>
            {isUser ? (
              <div className="fv-msg-user whitespace-pre-wrap break-words">
                {content}
              </div>
            ) : (
              <ChatMarkdown content={content} className="fv-msg-ai break-words" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

### `components/refinement/PressureTestSection.tsx`

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { Pencil } from "lucide-react";
import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";
import { ClarityAnswerCarousel } from "./ClarityAnswerCarousel";

interface PressureTestSectionProps {
  blocks: SourcedClarityQaBlock[];
  contentKey: string;
  messageContentById: Record<string, string>;
  canEditMessage: (messageId: string) => boolean;
  onEdit: (messageId: string, newContent: string) => Promise<void>;
}

function EditActions({
  saving,
  canSave,
  onSave,
  onCancel,
}: {
  saving: boolean;
  canSave: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !canSave}
        className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
      >
        Cancel
      </button>
    </div>
  );
}

/** Chapter 2 — all research-engine Q&A in one traversable card. */
export function PressureTestSection({
  blocks,
  contentKey,
  messageContentById,
  canEditMessage,
  onEdit,
}: PressureTestSectionProps) {
  const [index, setIndex] = useState(0);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const currentBlock = blocks[index];
  const editingContent = editingMessageId
    ? messageContentById[editingMessageId]
    : undefined;

  useEffect(() => {
    if (!editingMessageId) return;
    setDraft(editingContent ?? "");
  }, [editingMessageId, editingContent]);

  useEffect(() => {
    if (editingMessageId && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [editingMessageId]);

  const canEditCurrent =
    currentBlock != null && canEditMessage(currentBlock.messageId);

  const editButton =
    canEditCurrent && !editingMessageId ? (
      <button
        type="button"
        onClick={() => setEditingMessageId(currentBlock.messageId)}
        aria-label="Edit answers"
        className="rounded-md p-1.5 text-[var(--fv-text-muted)] transition-colors hover:bg-white/[0.06] hover:text-[var(--fv-text-soft)]"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    ) : null;

  async function handleSave() {
    if (!editingMessageId) return;
    const trimmed = draft.trim();
    const original = messageContentById[editingMessageId] ?? "";
    if (!trimmed || trimmed === original) {
      setEditingMessageId(null);
      return;
    }
    setSaving(true);
    try {
      await onEdit(editingMessageId, trimmed);
      setEditingMessageId(null);
    } finally {
      setSaving(false);
    }
  }

  if (blocks.length === 0) return null;

  return (
    <div className="fv-msg-enter">
      <section className="ra-section">
        <div className="ra-section-head">
          <div>
            <p className="ra-kicker">Chapter 2 · Pressure test</p>
            <h3 className="ra-section-title">You answered the hard questions.</h3>
          </div>
          {editButton}
        </div>

        {editingMessageId ? (
          <>
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={saving}
              rows={8}
              className="fv-input w-full resize-y px-3 py-2 font-mono text-[13px] leading-[1.55]"
            />
            <EditActions
              saving={saving}
              canSave={Boolean(draft.trim())}
              onSave={() => void handleSave()}
              onCancel={() => {
                setDraft(editingContent ?? "");
                setEditingMessageId(null);
              }}
            />
          </>
        ) : (
          <ClarityAnswerCarousel
            blocks={blocks}
            contentKey={contentKey}
            index={index}
            onIndexChange={setIndex}
          />
        )}
      </section>
    </div>
  );
}
```

### `components/refinement/ClarityAnswerCarousel.tsx`

```typescript
"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";

interface ClarityAnswerCarouselProps {
  blocks: SourcedClarityQaBlock[];
  contentKey: string;
  index: number;
  onIndexChange: (index: number) => void;
}

export function ClarityAnswerCarousel({
  blocks,
  contentKey,
  index,
  onIndexChange,
}: ClarityAnswerCarouselProps) {
  const total = blocks.length;
  const safeIndex = total > 0 ? Math.min(index, total - 1) : 0;
  const block = blocks[safeIndex];

  useEffect(() => {
    onIndexChange(0);
  }, [contentKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (index >= total && total > 0) {
      onIndexChange(total - 1);
    }
  }, [index, total, onIndexChange]);

  if (!block) return null;

  const canPrev = safeIndex > 0;
  const canNext = safeIndex < total - 1;

  return (
    <div className="ra-qa-carousel">
      {total > 1 && (
        <nav className="ra-qa-nav" aria-label="Question navigation">
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.max(0, safeIndex - 1))}
            disabled={!canPrev}
            aria-label="Previous question"
          >
            <ChevronLeft aria-hidden />
          </button>
          <span className="ra-qa-nav-count" aria-live="polite">
            {safeIndex + 1} of {total}
          </span>
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.min(total - 1, safeIndex + 1))}
            disabled={!canNext}
            aria-label="Next question"
          >
            <ChevronRight aria-hidden />
          </button>
        </nav>
      )}

      <article className="ra-qa-card">
        <p className="ra-qa-q">{block.question}</p>
        <ul className="ra-qa-list">
          {block.answers.map((answer) => (
            <li
              key={`${block.messageId}-${block.question}-${answer}`}
              className="ra-qa-list-item"
            >
              {answer}
            </li>
          ))}
        </ul>
      </article>
    </div>
  );
}
```

### `components/refinement/refinement-ascent.css`

```css
/* Refinement Ascent — editorial chapter layout (live refine thread) */

.ra-story {
  max-width: 42rem;
  margin: 0 auto;
  padding: 0.5rem 0 2rem;
}

.ra-kicker {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fv-accent);
}

.ra-kicker-light {
  color: color-mix(in srgb, white 70%, var(--fv-accent));
}

[data-theme="light"] .ra-kicker-light {
  color: color-mix(in srgb, var(--fv-text) 65%, var(--fv-accent));
}

.ra-hero {
  border-radius: 1.25rem;
  padding: 1.5rem 1.35rem 1.35rem;
  background: linear-gradient(
    165deg,
    color-mix(in srgb, var(--fv-accent) 14%, var(--fv-surface)),
    var(--fv-surface)
  );
  border: 1px solid color-mix(in srgb, var(--fv-accent) 22%, var(--fv-border));
}

.ra-hero-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.ra-hero-icon {
  display: inline-flex;
  margin-bottom: 0.85rem;
  padding: 0.55rem;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--fv-accent) 12%, transparent);
  color: var(--fv-accent);
}

.ra-hero-icon svg {
  width: 1.1rem;
  height: 1.1rem;
}

.ra-hero-title {
  margin: 0.35rem 0 0.85rem;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--fv-text);
}

.ra-hero-quote {
  margin: 0;
  padding-left: 0.85rem;
  border-left: 3px solid var(--fv-accent);
  font-size: 1rem;
  line-height: 1.7;
  font-weight: 500;
  color: var(--fv-text-soft);
  white-space: pre-wrap;
  word-break: break-word;
}

.ra-hero-byline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.85rem 0 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--fv-text-muted);
}

.ra-section {
  margin-top: 1.5rem;
}

.ra-section-continuation {
  margin-top: 0.75rem;
}

.ra-section-continuation .ra-section-head {
  justify-content: flex-end;
  margin-bottom: 0.5rem;
}

.ra-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.ra-section-title {
  margin: 0.35rem 0 1rem;
  font-size: 1.1rem;
  font-weight: 650;
  color: var(--fv-text);
}

.ra-qa-carousel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.ra-qa-card {
  border-radius: 0.85rem;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  padding: 1.1rem 1.15rem;
}

.ra-qa-q {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.45;
  color: var(--fv-text-muted);
}

.ra-qa-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.ra-qa-list-item {
  position: relative;
  padding-left: 1.1rem;
  font-size: 0.9375rem;
  line-height: 1.5;
  font-weight: 500;
  color: var(--fv-text);
}

.ra-qa-list-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--fv-accent);
}

.ra-qa-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.ra-qa-nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  color: var(--fv-text);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.ra-qa-nav-btn:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--fv-accent) 45%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-accent) 6%, var(--fv-surface));
  color: var(--fv-accent);
}

.ra-qa-nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.ra-qa-nav-btn svg {
  width: 1.1rem;
  height: 1.1rem;
}

.ra-qa-nav-count {
  min-width: 4.5rem;
  text-align: center;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--fv-text-muted);
}

.ra-finale {
  margin-top: 1.5rem;
  border-radius: 1.25rem;
  padding: 1.25rem;
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--fv-success) 20%, var(--fv-surface-elevated, var(--fv-surface))),
    color-mix(in srgb, var(--fv-accent) 14%, var(--fv-surface))
  );
  color: var(--fv-text);
  border: 1px solid color-mix(in srgb, var(--fv-success) 30%, var(--fv-border));
}

[data-theme="dark"] .ra-finale {
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--fv-success) 18%, #0f172a),
    color-mix(in srgb, var(--fv-accent) 22%, #111827)
  );
  color: #f8fafc;
  border-color: color-mix(in srgb, var(--fv-success) 35%, transparent);
}

.ra-finale-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
  border-radius: 999px;
  padding: 0.25rem 0.65rem;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  background: color-mix(in srgb, var(--fv-text) 8%, transparent);
}

[data-theme="dark"] .ra-finale-badge {
  background: color-mix(in srgb, white 12%, transparent);
}

.ra-finale-grid {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

@media (min-width: 560px) {
  .ra-finale-grid {
    grid-template-columns: 1fr auto 1.15fr;
    align-items: center;
  }
}

.ra-finale-before,
.ra-finale-after {
  border-radius: 0.75rem;
  padding: 0.75rem 0.85rem;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.ra-finale-before {
  background: color-mix(in srgb, var(--fv-text) 5%, transparent);
  color: var(--fv-text-soft);
}

.ra-finale-after {
  background: color-mix(in srgb, var(--fv-success) 10%, var(--fv-surface));
}

[data-theme="dark"] .ra-finale-before {
  background: color-mix(in srgb, white 6%, transparent);
  color: color-mix(in srgb, white 75%, transparent);
}

[data-theme="dark"] .ra-finale-after {
  background: color-mix(in srgb, white 14%, transparent);
}

.ra-finale-label {
  margin: 0 0 0.35rem;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.75;
}

.ra-finale-hypothesis {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.55;
}

.ra-finale-arrow {
  display: none;
  width: 1.25rem;
  height: 1.25rem;
  color: var(--fv-success);
  flex-shrink: 0;
}

[data-theme="dark"] .ra-finale-arrow {
  color: color-mix(in srgb, white 80%, var(--fv-success));
}

@media (min-width: 560px) {
  .ra-finale-arrow {
    display: block;
  }
}

.ra-default-row {
  padding: 0.35rem 0;
}

/* Active clarifying-question panel */
.ra-clarify-wrap {
  margin-top: 2rem;
}

.ra-clarify-panel {
  overflow: hidden;
  border-radius: 1.25rem;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 28%, var(--fv-border));
  background: var(--fv-surface);
}

.ra-clarify-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--fv-border);
  background: linear-gradient(
    165deg,
    color-mix(in srgb, var(--fv-accent) 10%, var(--fv-surface)),
    var(--fv-surface)
  );
}

.ra-clarify-kicker {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fv-accent);
}

.ra-clarify-title {
  margin: 0.35rem 0 0;
  font-size: 1.05rem;
  font-weight: 650;
  line-height: 1.3;
  color: var(--fv-text);
}

.ra-clarify-count {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--fv-text-muted);
}

.ra-clarify-panel-loading {
  border-style: dashed;
}

.ra-questions-loading-body {
  padding: 1.5rem;
}

.ra-questions-loading-skeleton {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.ra-questions-loading-line,
.ra-questions-loading-option {
  border-radius: 0.5rem;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--fv-border) 80%, transparent) 0%,
    color-mix(in srgb, var(--fv-accent) 12%, var(--fv-border)) 50%,
    color-mix(in srgb, var(--fv-border) 80%, transparent) 100%
  );
  background-size: 200% 100%;
  animation: ra-questions-shimmer 1.4s ease-in-out infinite;
}

.ra-questions-loading-line-title {
  height: 1.1rem;
  width: 88%;
}

.ra-questions-loading-option {
  height: 2.75rem;
  width: 100%;
}

.ra-questions-loading-option-short {
  width: 72%;
}

.ra-questions-loading-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.25rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--fv-text-muted);
}

.ra-questions-loading-slow {
  margin-top: 1rem;
  text-align: center;
}

.ra-questions-loading-slow-text {
  margin: 0 0 0.65rem;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--fv-text-muted);
}

@keyframes ra-questions-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
```

### `components/refinement/refinement-thread.css`

```css
/* Refinement thread — idea spark, clarity captures, refined hypothesis */

.rt-step {
  position: relative;
  padding: 0 0 1.75rem 2.75rem;
}

.rt-step::before {
  content: "";
  position: absolute;
  left: 0.95rem;
  top: 2.35rem;
  bottom: 0;
  width: 2px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--fv-accent) 35%, transparent),
    color-mix(in srgb, var(--fv-border) 80%, transparent)
  );
}

.rt-step:last-child::before {
  display: none;
}

.rt-step-marker {
  position: absolute;
  left: 0;
  top: 0.15rem;
  display: flex;
  height: 1.9rem;
  width: 1.9rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 35%, var(--fv-border));
  background: var(--fv-surface);
  color: var(--fv-accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--fv-accent) 8%, transparent);
}

.rt-step-marker svg {
  width: 0.95rem;
  height: 0.95rem;
}

.rt-step-marker-success {
  border-color: color-mix(in srgb, var(--fv-success) 40%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-success) 10%, var(--fv-surface));
  color: var(--fv-success);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--fv-success) 10%, transparent);
}

.rt-card {
  border: 1px solid var(--fv-border);
  border-radius: 1rem;
  background: var(--fv-surface);
  overflow: hidden;
}

.rt-card-spark {
  border-color: color-mix(in srgb, var(--fv-accent) 28%, var(--fv-border));
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--fv-accent) 9%, var(--fv-surface)),
    var(--fv-surface)
  );
  box-shadow:
    0 1px 0 color-mix(in srgb, white 6%, transparent) inset,
    0 12px 32px color-mix(in srgb, var(--fv-accent) 8%, transparent);
}

.rt-card-refined {
  border-color: color-mix(in srgb, var(--fv-success) 30%, var(--fv-border));
  background: linear-gradient(
    160deg,
    color-mix(in srgb, var(--fv-success) 8%, var(--fv-surface)),
    var(--fv-surface) 55%
  );
  box-shadow: 0 14px 36px color-mix(in srgb, var(--fv-success) 10%, transparent);
}

.rt-eyebrow {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.rt-eyebrow-accent {
  color: color-mix(in srgb, var(--fv-accent) 85%, var(--fv-text-muted));
}

.rt-eyebrow-success {
  color: color-mix(in srgb, var(--fv-success) 85%, var(--fv-text-muted));
}

.rt-card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.85rem 1rem 0;
}

.rt-card-body {
  padding: 0.65rem 1rem 1rem;
}

.rt-spark-text {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.65;
  font-weight: 500;
  color: var(--fv-text);
  letter-spacing: -0.01em;
}

.rt-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 25%, transparent);
  background: color-mix(in srgb, var(--fv-accent) 10%, transparent);
  color: var(--fv-accent);
}

.rt-badge-success {
  border-color: color-mix(in srgb, var(--fv-success) 30%, transparent);
  background: color-mix(in srgb, var(--fv-success) 10%, transparent);
  color: var(--fv-success);
}

.rt-clarity-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rt-clarity-item {
  border-radius: 0.75rem;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, var(--fv-text) 2%, transparent);
  padding: 0.75rem 0.85rem;
}

.rt-clarity-q {
  margin: 0 0 0.55rem;
  font-size: 0.78rem;
  font-weight: 650;
  line-height: 1.45;
  color: var(--fv-text-soft);
}

.rt-clarity-answers {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.rt-clarity-chip {
  display: inline-flex;
  max-width: 100%;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 22%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-accent) 7%, transparent);
  padding: 0.28rem 0.62rem;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--fv-text);
}

.rt-upgrade-grid {
  display: grid;
  gap: 0.75rem;
}

@media (min-width: 560px) {
  .rt-upgrade-grid {
    grid-template-columns: minmax(0, 0.9fr) auto minmax(0, 1.1fr);
    align-items: stretch;
  }
}

.rt-upgrade-before,
.rt-upgrade-after {
  border-radius: 0.75rem;
  padding: 0.75rem 0.85rem;
  min-width: 0;
}

.rt-upgrade-before {
  border: 1px dashed var(--fv-border-strong);
  background: color-mix(in srgb, var(--fv-text) 3%, transparent);
}

.rt-upgrade-after {
  border: 1px solid color-mix(in srgb, var(--fv-success) 28%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-success) 7%, transparent);
}

.rt-upgrade-label {
  margin: 0 0 0.4rem;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.rt-upgrade-text {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--fv-text-soft);
}

.rt-upgrade-text-strong {
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.55;
  color: var(--fv-text);
}

.rt-upgrade-arrow {
  display: none;
  align-items: center;
  justify-content: center;
  color: var(--fv-success);
}

@media (min-width: 560px) {
  .rt-upgrade-arrow {
    display: flex;
  }

  .rt-upgrade-arrow svg {
    width: 1.25rem;
    height: 1.25rem;
  }
}

.rt-default-row {
  padding: 0 0 1.25rem;
}

/* Peak clarifying question block */
.rt-clarify-panel {
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 28%, var(--fv-border));
  border-radius: 1rem;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--fv-accent) 7%, var(--fv-surface)),
    var(--fv-surface)
  );
  box-shadow: 0 10px 28px color-mix(in srgb, var(--fv-accent) 8%, transparent);
}

.rt-clarify-panel .rt-clarify-progress {
  border-bottom: 1px solid var(--fv-border);
  padding: 0.85rem 1rem;
  text-align: center;
}

.rt-clarify-panel .rt-clarify-progress-label {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fv-accent);
}

.rt-clarify-panel .rt-clarify-progress-count {
  margin: 0.2rem 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--fv-text-soft);
}
```

### `lib/clarifying-questions.ts`

```typescript
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";

export function createEmptyAnswers(
  questions: ClarifyingQuestion[],
): ClarifyingQuestionAnswer[] {
  return questions.map(() => ({ selectedOptions: [], otherText: "" }));
}

export function isQuestionAnswerValid(answer: ClarifyingQuestionAnswer): boolean {
  return answer.selectedOptions.length > 0 || answer.otherText.trim().length > 0;
}

export function formatClarifyingAnswers(
  questions: ClarifyingQuestion[],
  answers: ClarifyingQuestionAnswer[],
): string {
  return questions
    .map((question, index) => {
      const answer = answers[index];
      const parts: string[] = [...answer.selectedOptions];
      const other = answer.otherText.trim();
      if (other) {
        parts.push(`Other: ${other}`);
      }
      return `${question.question}\n→ ${parts.join("; ")}`;
    })
    .join("\n\n");
}

export function findPendingQuestionBlock(
  messages: {
    role: string;
    content?: string;
    turnKind?: string | null;
    clarifyingQuestions?: ClarifyingQuestion[];
  }[],
): { intro: string; questions: ClarifyingQuestion[] } | null {
  if (messages.length === 0) return null;
  const last = messages[messages.length - 1];
  if (last.role !== "assistant") return null;
  if (last.turnKind !== "refinement_clarify") return null;
  if (!last.clarifyingQuestions?.length) return null;
  return {
    intro: last.content ?? "",
    questions: last.clarifyingQuestions,
  };
}
```

### `lib/refinement-thread.ts`

```typescript
export interface ClarityQaBlock {
  question: string;
  answers: string[];
}

export interface SourcedClarityQaBlock extends ClarityQaBlock {
  messageId: string;
}

/** Flatten all clarifying-answer user messages into one ordered Q&A list. */
export function collectSourcedClarityBlocks(
  messages: ReadonlyArray<{ id: string; role: string; content: string }>,
  firstUserMessageId: string | null,
): SourcedClarityQaBlock[] {
  const result: SourcedClarityQaBlock[] = [];

  for (const msg of messages) {
    if (msg.role !== "user") continue;
    if (msg.id === firstUserMessageId) continue;
    const blocks = parseClarifyingAnswerContent(msg.content);
    if (!blocks) continue;
    for (const block of blocks) {
      result.push({ ...block, messageId: msg.id });
    }
  }

  return result;
}

/** User message body from formatClarifyingAnswers — question lines with → answers. */
export function parseClarifyingAnswerContent(
  content: string,
): ClarityQaBlock[] | null {
  const trimmed = content.trim();
  if (!trimmed.includes("\n→")) return null;

  const blocks = trimmed.split(/\n\n+/);
  const result: ClarityQaBlock[] = [];

  for (const block of blocks) {
    const arrowIdx = block.indexOf("\n→");
    if (arrowIdx === -1) return null;
    const question = block.slice(0, arrowIdx).trim();
    const answerLine = block.slice(arrowIdx + 2).trim();
    if (!question || !answerLine) return null;
    const answers = answerLine.split(/\s*;\s*/).filter(Boolean);
    result.push({ question, answers });
  }

  return result.length > 0 ? result : null;
}

/** Assistant finalize message — "Researching: …" */
export function parseResearchingHypothesis(content: string): string | null {
  const trimmed = content.trim();
  if (!/^researching:/i.test(trimmed)) return null;
  const hypothesis = trimmed.replace(/^researching:\s*/i, "").trim();
  return hypothesis || null;
}

/** Join multi-select answers for Refinement Ascent pull-quote style. */
export function formatAnswersAscent(answers: string[]): string {
  return answers.join(" · ");
}

export function excerptIdea(text: string, maxLen = 140): string {
  const oneLine = text.replace(/\s+/g, " ").trim();
  if (oneLine.length <= maxLen) return oneLine;
  return `${oneLine.slice(0, maxLen).trim()}…`;
}
```

### `components/wallet/ValidationResearchPrompt.tsx`

```typescript
"use client";

import { Coins, Sparkles } from "lucide-react";
import { VALIDATION_PAYWALL_CREDITS } from "@/lib/pricing";

interface ValidationResearchPromptProps {
  onStart: () => void;
  loading?: boolean;
}

/**
 * Shown after Chapter 3 (refinement finalize) — prompts user to run validation.
 */
export function ValidationResearchPrompt({
  onStart,
  loading = false,
}: ValidationResearchPromptProps) {
  return (
    <div className="fv-msg-enter mx-auto my-6 w-full max-w-full lg:max-w-[680px]">
      <div className="fv-validation-research-prompt">
        <div className="flex items-start gap-3">
          <span className="fv-validation-research-prompt-icon">
            <Sparkles className="h-5 w-5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-[var(--fv-text)]">
              Ready to validate your idea?
            </p>
            <p className="mt-1 text-sm leading-relaxed text-[var(--fv-text-muted)]">
              Run deep research, get a structured report, and generate a
              tracked landing page.
            </p>
            <p className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-text)]">
              <Coins className="h-4 w-4 text-[var(--fv-accent)]" aria-hidden />
              {VALIDATION_PAYWALL_CREDITS} Credits
            </p>
            <button
              type="button"
              onClick={onStart}
              disabled={loading}
              className="fv-btn-primary mt-4 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Starting…" : "Run validation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### Grep: clarifying_question | ClarifyingQuestion | refinement

```text
frontend\middleware.ts:19:  "/refinement-demos",
frontend\lib\clarifying-questions.ts:2:  ClarifyingQuestion,
frontend\lib\clarifying-questions.ts:3:  ClarifyingQuestionAnswer,
frontend\lib\clarifying-questions.ts:7:  questions: ClarifyingQuestion[],
frontend\lib\clarifying-questions.ts:8:): ClarifyingQuestionAnswer[] {
frontend\lib\clarifying-questions.ts:12:export function isQuestionAnswerValid(answer: ClarifyingQuestionAnswer): boolean {
frontend\lib\clarifying-questions.ts:17:  questions: ClarifyingQuestion[],
frontend\lib\clarifying-questions.ts:18:  answers: ClarifyingQuestionAnswer[],
frontend\lib\clarifying-questions.ts:38:    clarifyingQuestions?: ClarifyingQuestion[];
frontend\lib\clarifying-questions.ts:40:): { intro: string; questions: ClarifyingQuestion[] } | null {
frontend\lib\clarifying-questions.ts:44:  if (last.turnKind !== "refinement_clarify") return null;
frontend\app\refinement-demos\page.tsx:1:import { RefinementDemoShowcase } from "@/components/refinement-demos/RefinementDemoShowcase";
frontend\components\chat\ChatInterface.tsx:13:import type { ChatMessage as ChatMessageType, ChatTurnKind, ClarifyingQuestion, ClarifyingQuestionAnswer } from "@/lib/types";
frontend\components\chat\ChatInterface.tsx:17:import { ClarifyingQuestionBlock } from "@/components/refinement/ClarifyingQuestionBlock";
frontend\components\chat\ChatInterface.tsx:18:import { ClarifyingQuestionsLoading } from "@/components/refinement/ClarifyingQuestionsLoading";
frontend\components\chat\ChatInterface.tsx:19:import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
frontend\components\chat\ChatInterface.tsx:20:import { PressureTestSection } from "@/components/refinement/PressureTestSection";
frontend\components\chat\ChatInterface.tsx:28:} from "@/lib/refinement-thread";
frontend\components\chat\ChatInterface.tsx:106:    clarifying_questions?: ClarifyingQuestion[] | null;
frontend\components\chat\ChatInterface.tsx:115:    clarifyingQuestions: msg.clarifying_questions ?? undefined,
frontend\components\chat\ChatInterface.tsx:270:          (m) => m.turn_kind === "refinement_finalize",
frontend\components\chat\ChatInterface.tsx:410:        clarifyingQuestions: response.clarifying_questions,
frontend\components\chat\ChatInterface.tsx:416:        response.turn_kind === "refinement_finalize" &&
frontend\components\chat\ChatInterface.tsx:430:      if (createdNewExperiment || response.turn_kind === "refinement_finalize") {
frontend\components\chat\ChatInterface.tsx:434:      if (response.turn_kind === "refinement_finalize") {
frontend\components\chat\ChatInterface.tsx:443:      if (response.experiment_id && response.turn_kind === "refinement_finalize") {
frontend\components\chat\ChatInterface.tsx:626:    () => messages.some((m) => m.turnKind === "refinement_finalize"),
frontend\components\chat\ChatInterface.tsx:713:  function handleQuestionSubmit(answers: ClarifyingQuestionAnswer[]) {
frontend\components\chat\ChatInterface.tsx:821:                  msg.turnKind === "refinement_clarify" &&
frontend\components\chat\ChatInterface.tsx:853:                if (msg.turnKind === "refinement_finalize") {
frontend\components\chat\ChatInterface.tsx:930:                    <ClarifyingQuestionBlock
frontend\components\chat\ChatInterface.tsx:939:                    <ClarifyingQuestionsLoading
frontend\lib\experiment-stages.ts:115:/** Show stage tabs once refinement is complete (Chapter 3) or a report exists. */
frontend\lib\experiment-stages.ts:119:  refinementFinalized = false,
frontend\lib\experiment-stages.ts:121:  if (hasValidationReport || refinementFinalized) return true;
frontend\app\(dashboard)\new\page.tsx:1:import { RefineStagePanel } from "@/components/refinement/RefineStagePanel";
frontend\components\home\MarketingHero.tsx:7:    title: "AI refinement",
frontend\components\dashboard\ExperimentDetailPanel.tsx:23:import { RefineStagePanel } from "@/components/refinement/RefineStagePanel";
frontend\components\dashboard\ExperimentDetailPanel.tsx:124:  const [refinementFinalized, setRefinementFinalized] = useState(false);
frontend\components\dashboard\ExperimentDetailPanel.tsx:381:    refinementFinalized,
frontend\components\dashboard\ProjectCard.tsx:20:  REFINING: "AI refinement in progress",
frontend\components\wallet\ValidationResearchPrompt.tsx:12: * Shown after Chapter 3 (refinement finalize) â€” prompts user to run validation.
frontend\lib\types.ts:232:// --- Clarifying question block (refinement pre-research) ---
frontend\lib\types.ts:236:export interface ClarifyingQuestion {
frontend\lib\types.ts:242:export interface ClarifyingQuestionAnswer {
frontend\lib\types.ts:252:  clarifying_questions?: ClarifyingQuestion[] | null;
frontend\lib\types.ts:371:  | "refinement_clarify"
frontend\lib\types.ts:372:  | "refinement_finalize"
frontend\lib\types.ts:384:  clarifyingQuestions?: ClarifyingQuestion[];
frontend\lib\types.ts:395:  clarifying_questions?: ClarifyingQuestion[];
frontend\lib\types.ts:410:  clarifying_questions?: ClarifyingQuestion[];
frontend\lib\validation-report-score-details.ts:189:        ? ["Risk assessment engages specific risks from refinement."]
frontend\components\refinement\ClarifyingQuestionBlock.tsx:5:  ClarifyingQuestion,
frontend\components\refinement\ClarifyingQuestionBlock.tsx:6:  ClarifyingQuestionAnswer,
frontend\components\refinement\ClarifyingQuestionBlock.tsx:12:import "./refinement-ascent.css";
frontend\components\refinement\ClarifyingQuestionBlock.tsx:13:import "./refinement-thread.css";
frontend\components\refinement\ClarifyingQuestionBlock.tsx:15:interface ClarifyingQuestionBlockProps {
frontend\components\refinement\ClarifyingQuestionBlock.tsx:16:  questions: ClarifyingQuestion[];
frontend\components\refinement\ClarifyingQuestionBlock.tsx:22:  onSubmit: (answers: ClarifyingQuestionAnswer[]) => void;
frontend\components\refinement\ClarifyingQuestionBlock.tsx:25:export function ClarifyingQuestionBlock({
frontend\components\refinement\ClarifyingQuestionBlock.tsx:32:}: ClarifyingQuestionBlockProps) {
frontend\components\refinement\ClarifyingQuestionBlock.tsx:34:  const [answers, setAnswers] = useState<ClarifyingQuestionAnswer[]>(() =>
frontend\components\refinement\ClarifyingQuestionBlock.tsx:50:  function updateAnswer(next: ClarifyingQuestionAnswer) {
frontend\components\refinement\ClarityAnswerCarousel.tsx:5:import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";
frontend\components\refinement\ClarifyingQuestionsLoading.tsx:5:import "./refinement-ascent.css";
frontend\components\refinement\ClarifyingQuestionsLoading.tsx:7:interface ClarifyingQuestionsLoadingProps {
frontend\components\refinement\ClarifyingQuestionsLoading.tsx:14:export function ClarifyingQuestionsLoading({
frontend\components\refinement\ClarifyingQuestionsLoading.tsx:18:}: ClarifyingQuestionsLoadingProps) {
frontend\components\refinement\RefineStagePanel.tsx:11:/** Refine tab â€” chat-based idea refinement and validation. */
frontend\components\refinement\RefinementThreadMessage.tsx:22:} from "@/lib/refinement-thread";
frontend\components\refinement\RefinementThreadMessage.tsx:24:import "./refinement-ascent.css";
frontend\components\refinement\RefinementThreadMessage.tsx:25:import "./refinement-thread.css";
frontend\components\refinement\RefinementThreadMessage.tsx:37:  /** Label when rendered outside AuthProvider (e.g. refinement demos). */
frontend\components\refinement\RefinementThreadMessage.tsx:42:  /** Ascent is live in Refine; peak kept for /refinement-demos comparison. */
frontend\components\refinement\RefinementThreadMessage.tsx:106:    !isUser && turnKind === "refinement_finalize"
frontend\components\refinement\PressureTestSection.tsx:5:import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";
frontend\components\refinement-demos\RefinementAscentDemo.tsx:3:import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
frontend\components\refinement-demos\RefinementAscentDemo.tsx:4:import { PressureTestSection } from "@/components/refinement/PressureTestSection";
frontend\components\refinement-demos\RefinementAscentDemo.tsx:13:/** Live refinement thread styling â€” wired in ChatInterface. */
frontend\components\refinement-demos\RefinementAscentDemo.tsx:64:          turnKind="refinement_finalize"
frontend\components\refinement-demos\RefinementDemoShowcase.tsx:16:import "./refinement-demos.css";
frontend\components\refinement-demos\RefinementDemoShowcase.tsx:19:  "refinement-peak": () => <RefinementPeakDemo />,
frontend\components\refinement-demos\RefinementDemoShowcase.tsx:20:  "refinement-ascent": () => <RefinementAscentDemo />,
frontend\components\refinement-demos\RefinementDemoShowcase.tsx:31:  const [activeId, setActiveId] = useState("refinement-ascent");
frontend\components\refinement-demos\RefinementPeakDemo.tsx:3:import { RefinementThreadMessage } from "@/components/refinement/RefinementThreadMessage";
frontend\components\refinement-demos\RefinementPeakDemo.tsx:12:/** Live refinement thread styling â€” wired in ChatInterface. */
frontend\components\refinement-demos\RefinementPeakDemo.tsx:48:          turnKind="refinement_finalize"
frontend\components\refinement-demos\shared.ts:1:/** Shared sample idea for all refinement UI demos (Mewwly-style dating app). */
frontend\components\refinement-demos\shared.ts:39:    id: "refinement-ascent",
frontend\components\refinement-demos\shared.ts:44:    id: "refinement-peak",
frontend\components\refinement-demos\shared.ts:50:    title: "Guided refinement",
frontend\components\refinement-demos\quest-map\QuestMapExperience.tsx:5:/** Demo showcase â€” live chat refinement UI. */
```

## 3. Wizard / clarifying question rendering

### `components/refinement/ClarifyingQuestionBlock.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";
import {
  createEmptyAnswers,
  isQuestionAnswerValid,
} from "@/lib/clarifying-questions";
import "./refinement-ascent.css";
import "./refinement-thread.css";

interface ClarifyingQuestionBlockProps {
  questions: ClarifyingQuestion[];
  intro?: string;
  /** 1-based index for the first question in this batch (continues across rounds). */
  questionNumberStart?: number;
  submitting?: boolean;
  variant?: "default" | "ascent" | "peak";
  onSubmit: (answers: ClarifyingQuestionAnswer[]) => void;
}

export function ClarifyingQuestionBlock({
  questions,
  intro,
  questionNumberStart = 1,
  submitting = false,
  variant = "default",
  onSubmit,
}: ClarifyingQuestionBlockProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<ClarifyingQuestionAnswer[]>(() =>
    createEmptyAnswers(questions),
  );
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentIndex(0);
    setAnswers(createEmptyAnswers(questions));
    setValidationError(null);
  }, [questions]);

  const currentQuestion = questions[currentIndex];
  const currentAnswer = answers[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === questions.length - 1;

  function updateAnswer(next: ClarifyingQuestionAnswer) {
    setAnswers((prev) =>
      prev.map((item, idx) => (idx === currentIndex ? next : item)),
    );
    setValidationError(null);
  }

  function toggleOption(optionIndex: number) {
    const option = currentQuestion.options[optionIndex];
    const selected = new Set(currentAnswer.selectedOptions);
    if (selected.has(option)) {
      selected.delete(option);
    } else {
      selected.add(option);
    }
    updateAnswer({
      selectedOptions: [...selected],
      otherText: currentAnswer.otherText,
    });
  }

  function handlePrevious() {
    setValidationError(null);
    setCurrentIndex((idx) => Math.max(0, idx - 1));
  }

  function handleNext() {
    if (!isQuestionAnswerValid(currentAnswer)) {
      setValidationError(
        "Select at least one option (you can pick multiple) or enter a custom answer.",
      );
      return;
    }
    setValidationError(null);
    if (isLast) {
      onSubmit(answers);
      return;
    }
    setCurrentIndex((idx) => idx + 1);
  }

  const isAscent = variant === "ascent" || variant === "peak";
  const isPeak = variant === "peak";
  const isAscentLive = variant === "ascent";
  const globalQuestionNumber = questionNumberStart + currentIndex;

  return (
    <div
      className={`fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ${
        isAscentLive ? "ra-clarify-wrap" : ""
      }`}
    >
      <div
        className={
          isAscent
            ? isPeak
              ? "rt-clarify-panel"
              : "ra-clarify-panel"
            : "overflow-hidden rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)]"
        }
      >
        <div
          className={
            isAscent
              ? isPeak
                ? "rt-clarify-progress"
                : "ra-clarify-header"
              : "border-b border-[var(--fv-border)] px-6 py-4 text-center"
          }
        >
          {isAscent ? (
            isPeak ? (
              <>
                <p className="rt-clarify-progress-label">Sharpen your idea</p>
                <p className="rt-clarify-progress-count">
                  Question {currentIndex + 1} of {questions.length}
                </p>
              </>
            ) : (
              <>
                <h3 className="ra-clarify-title">Sharpen your idea</h3>
                <p className="ra-clarify-count">
                  Question {globalQuestionNumber}
                </p>
              </>
            )
          ) : (
            <p className="text-sm font-medium text-[var(--fv-text-muted)]">
              {currentIndex + 1} / {questions.length}
            </p>
          )}
        </div>

        <div className="space-y-6 px-6 py-6">
          {intro && currentIndex === 0 && !isAscentLive && (
            <p className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
              {intro}
            </p>
          )}

          <div>
            <h3 className="text-base font-semibold text-[var(--fv-text)]">
              {isAscentLive
                ? `${globalQuestionNumber}. ${currentQuestion.question}`
                : `Q${currentIndex + 1}. ${currentQuestion.question}`}
            </h3>
            <p className="mt-1.5 text-xs text-[var(--fv-text-muted)]">
              You can select multiple options — choose every answer that applies.
            </p>
          </div>

          <ol className="space-y-3">
            {currentQuestion.options.map((option, optionIndex) => {
              const selected = currentAnswer.selectedOptions.includes(option);

              return (
                <li key={`${currentIndex}-${optionIndex}`}>
                  <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--fv-border)] px-4 py-3 transition-colors hover:border-[var(--fv-accent)]/40 hover:bg-[var(--fv-accent)]/5 has-[:checked]:border-[var(--fv-accent)]/50 has-[:checked]:bg-[var(--fv-accent)]/5">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={submitting}
                      onChange={() => toggleOption(optionIndex)}
                      className="mt-0.5 shrink-0 accent-[var(--fv-accent)]"
                    />
                    <span className="text-sm leading-relaxed text-[var(--fv-text)]">
                      <span className="mr-2 font-medium text-[var(--fv-text-muted)]">
                        {optionIndex + 1}.
                      </span>
                      {option}
                    </span>
                  </label>
                </li>
              );
            })}

            <li>
              <label className="flex flex-col gap-2 rounded-lg border border-[var(--fv-border)] px-4 py-3">
                <span className="text-sm font-medium text-[var(--fv-text)]">
                  {currentQuestion.options.length + 1}. Other:
                </span>
                <input
                  type="text"
                  value={currentAnswer.otherText}
                  disabled={submitting}
                  onChange={(e) =>
                    updateAnswer({
                      selectedOptions: currentAnswer.selectedOptions,
                      otherText: e.target.value,
                    })
                  }
                  placeholder="Type your answer…"
                  className="fv-input w-full px-3 py-2 text-sm"
                />
              </label>
            </li>
          </ol>

          {validationError && (
            <p className="text-sm text-[var(--fv-danger)]">{validationError}</p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-[var(--fv-border)] px-6 py-4">
          <button
            type="button"
            onClick={handlePrevious}
            disabled={isFirst || submitting}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={submitting}
            className="fv-btn-primary px-5 py-2 text-sm disabled:opacity-50"
          >
            {submitting ? "Submitting…" : isLast ? "Submit" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

### `components/refinement/ClarityAnswerCarousel.tsx`

```typescript
"use client";

import { useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { SourcedClarityQaBlock } from "@/lib/refinement-thread";

interface ClarityAnswerCarouselProps {
  blocks: SourcedClarityQaBlock[];
  contentKey: string;
  index: number;
  onIndexChange: (index: number) => void;
}

export function ClarityAnswerCarousel({
  blocks,
  contentKey,
  index,
  onIndexChange,
}: ClarityAnswerCarouselProps) {
  const total = blocks.length;
  const safeIndex = total > 0 ? Math.min(index, total - 1) : 0;
  const block = blocks[safeIndex];

  useEffect(() => {
    onIndexChange(0);
  }, [contentKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (index >= total && total > 0) {
      onIndexChange(total - 1);
    }
  }, [index, total, onIndexChange]);

  if (!block) return null;

  const canPrev = safeIndex > 0;
  const canNext = safeIndex < total - 1;

  return (
    <div className="ra-qa-carousel">
      {total > 1 && (
        <nav className="ra-qa-nav" aria-label="Question navigation">
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.max(0, safeIndex - 1))}
            disabled={!canPrev}
            aria-label="Previous question"
          >
            <ChevronLeft aria-hidden />
          </button>
          <span className="ra-qa-nav-count" aria-live="polite">
            {safeIndex + 1} of {total}
          </span>
          <button
            type="button"
            className="ra-qa-nav-btn"
            onClick={() => onIndexChange(Math.min(total - 1, safeIndex + 1))}
            disabled={!canNext}
            aria-label="Next question"
          >
            <ChevronRight aria-hidden />
          </button>
        </nav>
      )}

      <article className="ra-qa-card">
        <p className="ra-qa-q">{block.question}</p>
        <ul className="ra-qa-list">
          {block.answers.map((answer) => (
            <li
              key={`${block.messageId}-${block.question}-${answer}`}
              className="ra-qa-list-item"
            >
              {answer}
            </li>
          ))}
        </ul>
      </article>
    </div>
  );
}
```

### `lib/clarifying-questions.ts`

```typescript
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
} from "@/lib/types";

export function createEmptyAnswers(
  questions: ClarifyingQuestion[],
): ClarifyingQuestionAnswer[] {
  return questions.map(() => ({ selectedOptions: [], otherText: "" }));
}

export function isQuestionAnswerValid(answer: ClarifyingQuestionAnswer): boolean {
  return answer.selectedOptions.length > 0 || answer.otherText.trim().length > 0;
}

export function formatClarifyingAnswers(
  questions: ClarifyingQuestion[],
  answers: ClarifyingQuestionAnswer[],
): string {
  return questions
    .map((question, index) => {
      const answer = answers[index];
      const parts: string[] = [...answer.selectedOptions];
      const other = answer.otherText.trim();
      if (other) {
        parts.push(`Other: ${other}`);
      }
      return `${question.question}\n→ ${parts.join("; ")}`;
    })
    .join("\n\n");
}

export function findPendingQuestionBlock(
  messages: {
    role: string;
    content?: string;
    turnKind?: string | null;
    clarifyingQuestions?: ClarifyingQuestion[];
  }[],
): { intro: string; questions: ClarifyingQuestion[] } | null {
  if (messages.length === 0) return null;
  const last = messages[messages.length - 1];
  if (last.role !== "assistant") return null;
  if (last.turnKind !== "refinement_clarify") return null;
  if (!last.clarifyingQuestions?.length) return null;
  return {
    intro: last.content ?? "",
    questions: last.clarifyingQuestions,
  };
}
```

### `components/refinement/ClarifyingQuestionsLoading.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import "./refinement-ascent.css";

interface ClarifyingQuestionsLoadingProps {
  questionNumber: number;
  phase?: "submitting" | "syncing";
  onRetry?: () => void;
}

/** Shown while waiting for the next clarifying question — not the chat typing indicator. */
export function ClarifyingQuestionsLoading({
  questionNumber,
  phase = "submitting",
  onRetry,
}: ClarifyingQuestionsLoadingProps) {
  const [showSlowHint, setShowSlowHint] = useState(false);

  useEffect(() => {
    setShowSlowHint(false);
    const timer = window.setTimeout(() => setShowSlowHint(true), 25_000);
    return () => window.clearTimeout(timer);
  }, [questionNumber, phase]);

  const statusLabel =
    phase === "syncing"
      ? "Checking for your next question…"
      : "Preparing your next question…";

  return (
    <div className="fv-msg-enter mx-auto w-full max-w-full lg:max-w-[42rem] ra-clarify-wrap">
      <div className="ra-clarify-panel ra-clarify-panel-loading" aria-busy="true">
        <div className="ra-clarify-header">
          <h3 className="ra-clarify-title">Sharpen your idea</h3>
          <p className="ra-clarify-count">Question {questionNumber}</p>
        </div>

        <div className="ra-questions-loading-body">
          <div className="ra-questions-loading-skeleton" aria-hidden>
            <div className="ra-questions-loading-line ra-questions-loading-line-title" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option" />
            <div className="ra-questions-loading-option ra-questions-loading-option-short" />
          </div>

          <div className="ra-questions-loading-status">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--fv-accent)]" />
            <span>{statusLabel}</span>
          </div>

          {showSlowHint && (
            <div className="ra-questions-loading-slow">
              <p className="ra-questions-loading-slow-text">
                {phase === "syncing"
                  ? "Still waiting on Fivvle. You can refresh to pull the latest questions."
                  : "This is taking longer than usual. Fivvle is still working on your next question."}
              </p>
              {onRetry ? (
                <button
                  type="button"
                  onClick={onRetry}
                  className="fv-btn-ghost px-3 py-1.5 text-sm"
                >
                  Refresh
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## 4. Report reader

### `app/(dashboard)/experiment/[id]/page.tsx`

```typescript
"use client";

import { ExperimentDetailPanel } from "@/components/dashboard/ExperimentDetailPanel";
import type { ExperimentStageId } from "@/lib/experiment-stages";
import { useParams, useSearchParams } from "next/navigation";

function parseInitialStage(value: string | null): ExperimentStageId | undefined {
  if (
    value === "refine" ||
    value === "report" ||
    value === "landing" ||
    value === "metrics" ||
    value === "insight"
  ) {
    return value;
  }
  return undefined;
}

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const initialStage = parseInitialStage(searchParams.get("stage"));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExperimentDetailPanel
        experimentId={params.id}
        initialStage={initialStage}
      />
    </div>
  );
}
```

### `components/research/ValidationReportPanel.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  X,
} from "lucide-react";
import { getValidationReport, ApiError } from "@/lib/api";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";
import { ReportScoreSection } from "@/components/research/ReportScoreSection";
import { resolveReportScores } from "@/lib/validation-report-scores";

const REPORT_TABS = [
  "Summary",
  "Findings",
  "Competitors",
  "Signals",
  "Risks",
  "Citations",
] as const;

type ReportTab = (typeof REPORT_TABS)[number];

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function recommendationBadgeClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "badge-proceed";
    case "iterate":
      return "badge-iterate";
    case "pivot":
      return "badge-pivot";
    case "kill":
      return "badge-kill";
    default:
      return "unavailable-badge";
  }
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "UNCLEAR";
  return rec.toUpperCase();
}

function confidenceClass(confidence: Finding["confidence"]): string {
  switch (confidence) {
    case "high":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "medium":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "low":
      return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
  }
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-sm text-[var(--fv-text-muted)]">
        {citation.title}
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] no-underline"
    >
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
    </a>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="fv-card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="whitespace-pre-wrap text-[13px] font-medium text-[var(--fv-text)]">
        {finding.claim}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-[13px] text-[var(--fv-text-soft)]">
        {finding.evidence_summary}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-[12px] text-[var(--fv-text-muted)]">
        {finding.confidence_rationale}
      </p>
      {finding.citations.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-[var(--fv-border)] pt-2">
          {finding.citations.map((c) => (
            <SafeCitationLink key={c.url} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function QuestionSection({
  question,
  defaultOpen,
}: {
  question: ValidationReport["questions_and_findings"][number];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-[var(--fv-border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 py-4 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        ) : (
          <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        )}
        <span className="text-[13px] font-semibold text-[var(--fv-text)]">
          {question.question}
        </span>
      </button>
      {open && (
        <div className="space-y-3 pb-4 pl-7">
          {question.findings.map((finding) => (
            <FindingCard key={`${finding.question_id}-${finding.claim}`} finding={finding} />
          ))}
          {question.evidence_gap && (
            <p className="whitespace-pre-wrap text-[12px] text-[var(--fv-warning)]">
              Evidence gap: {question.evidence_gap}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function collectAllCitations(report: ValidationReport): Citation[] {
  const seen = new Set<string>();
  const citations: Citation[] = [];

  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      for (const c of finding.citations) {
        const key = c.url || c.title;
        if (!seen.has(key)) {
          seen.add(key);
          citations.push(c);
        }
      }
    }
  }
  for (const comp of report.competitors) {
    for (const c of comp.citations) {
      const key = c.url || c.title;
      if (!seen.has(key)) {
        seen.add(key);
        citations.push(c);
      }
    }
  }
  return citations;
}

interface ValidationReportPanelProps {
  experimentId: string;
  open: boolean;
  onClose: () => void;
}

export function ValidationReportPanel({
  experimentId,
  open,
  onClose,
}: ValidationReportPanelProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("Summary");

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getValidationReport(experimentId);
        if (!cancelled) setReport(data);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? "Could not load the validation report."
            : "Could not load the validation report.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [experimentId, open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const citations = report ? collectAllCitations(report) : [];
  const reportScores = report ? resolveReportScores(report) : null;

  if (!open) return null;

  return (
    <div
      className="flex h-full min-h-0 flex-col bg-[var(--fv-surface)]"
      role="region"
      aria-label="Validation Report"
    >
        <div
          className="flex items-center justify-between border-b px-5 py-4"
          style={{ borderColor: "rgba(255,255,255,0.07)" }}
        >
          <div className="flex items-center gap-3">
            <h2 className="text-[15px] font-bold text-[var(--fv-text)]">
              Validation Report
            </h2>
            {report && (
              <span
                className={recommendationBadgeClass(report.overall_recommendation)}
              >
                {formatRecommendation(report.overall_recommendation)}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="icon-btn"
            aria-label="Close report"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div
          className="flex gap-1 border-b px-4 py-3"
          style={{ borderColor: "rgba(255,255,255,0.07)" }}
        >
          {REPORT_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`report-tab ${activeTab === tab ? "active" : ""}`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="px-6 py-5">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
            </div>
          )}

          {error && (
            <div className="fv-error text-sm">{error}</div>
          )}

          {report && !loading && activeTab === "Summary" && reportScores && (
            <div className="space-y-5">
              <ReportScoreSection
                report={report}
                sections={reportScores.sections}
                overall={reportScores.overall}
                derived={reportScores.derived}
              />

              <div>
                <h3 className="fv-panel-label mb-3">Executive Summary</h3>
                <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-[var(--fv-text-soft)]">
                  {report.executive_summary}
                </p>
              </div>

              <div
                className="rounded-xl p-4"
                style={{
                  background: "rgba(16,185,129,0.08)",
                  border: "1px solid rgba(16,185,129,0.2)",
                }}
              >
                <p className="text-[13px] font-semibold text-fv-success">
                  Recommendation: {formatRecommendation(report.overall_recommendation)}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                  {report.recommendation_rationale}
                </p>
              </div>

              <div>
                <h3 className="fv-panel-label mb-3">Market Signals</h3>
                {report.market_signals ? (
                  <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                    {report.market_signals}
                  </p>
                ) : (
                  <span className="unavailable-badge">Data unavailable</span>
                )}
              </div>

              {report.research_limitations && (
                <div>
                  <h3 className="fv-panel-label mb-3">Research Limitations</h3>
                  <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-muted)]">
                    {report.research_limitations}
                  </p>
                </div>
              )}
            </div>
          )}

          {report && !loading && activeTab === "Findings" && (
            <div>
              {report.questions_and_findings.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No research findings available.
                </p>
              ) : (
                report.questions_and_findings.map((qf, i) => (
                  <QuestionSection key={qf.question_id} question={qf} defaultOpen={i === 0} />
                ))
              )}
            </div>
          )}

          {report && !loading && activeTab === "Competitors" && (
            <div className="space-y-3">
              {report.competitors.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No competitors identified.
                </p>
              ) : (
                report.competitors.map((comp) => (
                  <div key={comp.name} className="fv-card p-4">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="text-[14px] font-semibold text-[var(--fv-text)]">
                        {comp.name}
                      </p>
                      <span className="severity-medium">Competitor</span>
                    </div>
                    <p className="text-[13px] text-[var(--fv-text-soft)]">
                      {comp.description}
                    </p>
                    <p className="mt-2 text-[12px] text-[var(--fv-text-muted)]">
                      Gap: {comp.positioning_vs_idea}
                    </p>
                    {comp.citations.length > 0 && (
                      <div className="mt-3 space-y-1 border-t border-[var(--fv-border)] pt-2">
                        {comp.citations.map((c) => (
                          <SafeCitationLink key={c.url} citation={c} />
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {report && !loading && activeTab === "Signals" && (
            <div className="space-y-6">
              {(
                [
                  ["Market", report.market_signals],
                  ["Distribution", report.distribution_signals],
                  ["Regulatory", report.regulatory_signals],
                ] as const
              ).map(([group, text]) => (
                <div key={group}>
                  <h3 className="fv-panel-label mb-3">{group}</h3>
                  {text ? (
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                      {text}
                    </p>
                  ) : (
                    <span className="unavailable-badge">Data unavailable</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {report && !loading && activeTab === "Risks" && (
            <div className="space-y-3">
              {report.risks_assessment ? (
                report.risks_assessment
                  .split("\n")
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .map((risk, i) => (
                    <div key={i} className="fv-card p-4">
                      <div className="mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-[var(--fv-warning)]" />
                        <span className="severity-high">Risk</span>
                      </div>
                      <p className="text-[13px] leading-relaxed text-[var(--fv-text-soft)]">
                        {risk}
                      </p>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No significant risks identified.
                </p>
              )}
            </div>
          )}

          {report && !loading && activeTab === "Citations" && (
            <div className="space-y-3">
              {citations.length === 0 ? (
                <p className="text-sm text-[var(--fv-text-muted)]">
                  No citations available.
                </p>
              ) : (
                citations.map((citation, i) => (
                  <div key={`${citation.url}-${i}`} className="flex items-start gap-3">
                    <span
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-fv-bg"
                      style={{ background: "var(--fv-accent)" }}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <SafeCitationLink citation={citation} />
                      <p className="mt-0.5 text-[11px] text-[var(--fv-text-muted)]">
                        {citation.source_domain}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
    </div>
  );
}
```

### `components/research/ValidationReportViewer.tsx`

```typescript
"use client";

import { useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { getValidationReport, ApiError } from "@/lib/api";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return (
      <span className="text-sm text-[var(--fv-text-muted)]">
        {citation.title} ({citation.source_domain})
      </span>
    );
  }

  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-sm text-[var(--fv-accent)] hover:text-[var(--fv-accent-hover)] hover:underline"
    >
      {citation.title}
      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
      <span className="text-[var(--fv-text-muted)]">({citation.source_domain})</span>
    </a>
  );
}

function confidenceClass(confidence: Finding["confidence"]): string {
  switch (confidence) {
    case "high":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "medium":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "low":
      return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
  }
}

function recommendationClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "bg-[rgba(16,185,129,0.15)] text-[var(--fv-success)] ring-[rgba(16,185,129,0.3)]";
    case "iterate":
      return "bg-[var(--fv-accent-muted)] text-[var(--fv-accent)] ring-[color-mix(in_srgb,var(--fv-accent)_30%,transparent)]";
    case "pivot":
      return "bg-[rgba(245,158,11,0.15)] text-[var(--fv-warning)] ring-[rgba(245,158,11,0.3)]";
    case "kill":
      return "bg-[rgba(239,68,68,0.15)] text-red-300 ring-[rgba(239,68,68,0.3)]";
    case "too_vague_to_recommend":
      return "bg-white/10 text-[var(--fv-text-soft)] ring-white/10";
  }
}

function formatRecommendation(rec: OverallRecommendation): string {
  return rec
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="fv-card p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="whitespace-pre-wrap text-sm font-medium text-[var(--fv-text)]">
        {finding.claim}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
        {finding.evidence_summary}
      </p>
      <p className="mt-2 whitespace-pre-wrap text-xs text-[var(--fv-text-muted)]">
        {finding.confidence_rationale}
      </p>
      {finding.citations.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-[var(--fv-border)] pt-3">
          {finding.citations.map((citation) => (
            <li key={`${citation.url}-${citation.title}`}>
              <SafeCitationLink citation={citation} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QuestionSection({
  question,
  defaultOpen,
}: {
  question: ValidationReport["questions_and_findings"][number];
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-[var(--fv-border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 py-4 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        ) : (
          <ChevronRight className="mt-0.5 h-5 w-5 shrink-0 text-[var(--fv-text-muted)]" />
        )}
        <span className="text-sm font-semibold text-[var(--fv-text)]">
          {question.question}
        </span>
      </button>
      {open && (
        <div className="space-y-3 pb-4 pl-7">
          {question.findings.map((finding) => (
            <FindingCard key={`${finding.question_id}-${finding.claim}`} finding={finding} />
          ))}
          {question.evidence_gap && (
            <p className="whitespace-pre-wrap text-xs text-[var(--fv-warning)]">
              Evidence gap: {question.evidence_gap}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface ValidationReportViewerProps {
  experimentId: string;
  onGenerateLandingPage?: () => void;
  generatingLandingPage?: boolean;
}

export function ValidationReportViewer({
  experimentId,
  onGenerateLandingPage,
  generatingLandingPage = false,
}: ValidationReportViewerProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getValidationReport(experimentId);
        if (!cancelled) setReport(data);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? "Could not load the validation report."
            : "Could not load the validation report.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="fv-error px-6 py-8 text-center">
        <p className="text-sm">
          {error ?? "Validation report not available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">
          Executive summary
        </h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.executive_summary}
        </p>
        {report.market_signals && (
          <>
            <h3 className="mt-6 text-sm font-semibold text-[var(--fv-text)]">
              Market signals
            </h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-muted)]">
              {report.market_signals}
            </p>
          </>
        )}
      </section>

      <section className="fv-card px-6">
        <h2 className="border-b border-[var(--fv-border)] py-4 text-lg font-semibold text-[var(--fv-text)]">
          Research questions & findings
        </h2>
        {report.questions_and_findings.map((qf, i) => (
          <QuestionSection key={qf.question_id} question={qf} defaultOpen={i === 0} />
        ))}
      </section>

      {report.competitors.length > 0 && (
        <section className="fv-card p-6">
          <h2 className="text-lg font-semibold text-[var(--fv-text)]">Competitors</h2>
          <ul className="mt-4 space-y-4">
            {report.competitors.map((comp) => (
              <li
                key={comp.name}
                className="fv-card p-4"
              >
                <p className="font-medium text-[var(--fv-text)]">{comp.name}</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
                  {comp.description}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--fv-text-soft)]">
                  {comp.positioning_vs_idea}
                </p>
                {comp.citations.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {comp.citations.map((citation) => (
                      <li key={`${comp.name}-${citation.url}`}>
                        <SafeCitationLink citation={citation} />
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">Risks</h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.risks_assessment}
        </p>
      </section>

      <section className="fv-card p-6">
        <h2 className="text-lg font-semibold text-[var(--fv-text)]">Recommendation</h2>
        <span
          className={`mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${recommendationClass(report.overall_recommendation)}`}
        >
          {formatRecommendation(report.overall_recommendation)}
        </span>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-[var(--fv-text-soft)]">
          {report.recommendation_rationale}
        </p>
        {report.research_limitations && (
          <p className="mt-4 whitespace-pre-wrap text-xs text-[var(--fv-text-muted)]">
            Limitations: {report.research_limitations}
          </p>
        )}
      </section>

      {onGenerateLandingPage && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onGenerateLandingPage}
            disabled={generatingLandingPage}
            className="fv-btn-primary px-5 py-2.5 text-sm disabled:cursor-not-allowed"
          >
            {generatingLandingPage && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Generate Landing Page
          </button>
        </div>
      )}
    </div>
  );
}
```

### `components/research/ReportCanvas.tsx`

```typescript
"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Building2,
  ChevronDown,
  ExternalLink,
  FileText,
  Maximize2,
  Minimize2,
  TrendingUp,
  X,
} from "lucide-react";
import { getValidationReport } from "@/lib/api";
import {
  parseRiskAssessment,
  questionDisplayIndex,
  splitReadableParagraphs,
} from "@/lib/report-text";
import {
  resolveQuestionScore,
  resolveReportScores,
} from "@/lib/validation-report-scores";
import { ValidationReportExportMenu } from "@/components/research/ValidationReportExportMenu";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "@/lib/types";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { ReportScoreSection } from "@/components/research/ReportScoreSection";
import "./report-canvas.css";

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function SafeCitationLink({ citation }: { citation: Citation }) {
  if (!isSafeHttpUrl(citation.url)) {
    return <span className="text-[var(--fv-text)]">{citation.title}</span>;
  }
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-[var(--fv-accent)] no-underline hover:underline"
    >
      {citation.title}
      <ExternalLink className="h-3 w-3 opacity-60" />
    </a>
  );
}

function recommendationBadgeClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "badge-proceed";
    case "iterate":
      return "badge-iterate";
    case "pivot":
      return "badge-pivot";
    case "kill":
      return "badge-kill";
    default:
      return "unavailable-badge";
  }
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function confidenceClass(confidence: string): string {
  if (confidence === "high") return "fv-confidence-high";
  if (confidence === "medium") return "fv-confidence-medium";
  return "fv-confidence-low";
}

function findingAccentClass(confidence: string): string {
  if (confidence === "high") return "report-finding-high";
  if (confidence === "medium") return "report-finding-medium";
  return "report-finding-low";
}

function collectAllCitations(report: ValidationReport): Citation[] {
  const seen = new Set<string>();
  const citations: Citation[] = [];
  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      for (const c of finding.citations) {
        const key = c.url || c.title;
        if (!seen.has(key)) {
          seen.add(key);
          citations.push(c);
        }
      }
    }
  }
  for (const comp of report.competitors) {
    for (const c of comp.citations) {
      const key = c.url || c.title;
      if (!seen.has(key)) {
        seen.add(key);
        citations.push(c);
      }
    }
  }
  return citations;
}

function buildCitationIndexMap(citations: Citation[]): Map<string, number> {
  const map = new Map<string, number>();
  citations.forEach((citation, index) => {
    map.set(citation.url || citation.title, index + 1);
  });
  return map;
}

function countFindings(report: ValidationReport): number {
  return report.questions_and_findings.reduce(
    (total, qf) => total + qf.findings.length,
    0,
  );
}

function ReadableProse({ text }: { text: string }) {
  const paragraphs = splitReadableParagraphs(text);
  return (
    <div className="report-prose">
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

function RiskAssessmentContent({ text }: { text: string }) {
  const parsed = parseRiskAssessment(text);

  if (!parsed.isStructured) {
    return <ReadableProse text={text} />;
  }

  return (
    <div>
      {parsed.preamble && (
        <div className="report-risk-preamble">
          {splitReadableParagraphs(parsed.preamble, 420).map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-2" : undefined}>
              {paragraph}
            </p>
          ))}
        </div>
      )}
      <ol className="report-risk-list">
        {parsed.items.map((risk) => (
          <li key={risk.number} className="report-risk-item">
            <div className="report-risk-header">
              <span className="report-risk-num" aria-hidden="true">
                {risk.number}
              </span>
              <div className="report-risk-heading">
                <h3 className="report-risk-title">{risk.title}</h3>
                {risk.verdict && (
                  <span className="report-risk-verdict">{risk.verdict}</span>
                )}
              </div>
            </div>
            {risk.body && (
              <div className="report-risk-body">
                {splitReadableParagraphs(risk.body, 420).map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function CitationRefs({
  citations,
  citationIndexMap,
}: {
  citations: Citation[];
  citationIndexMap: Map<string, number>;
}) {
  if (citations.length === 0) return null;
  return (
    <>
      {citations.map((citation) => {
        const key = citation.url || citation.title;
        const index = citationIndexMap.get(key);
        if (!index) return null;
        return (
          <a
            key={key}
            href={`#citation-${index}`}
            className="report-cite-ref"
            title={citation.title}
          >
            [{index}]
          </a>
        );
      })}
    </>
  );
}

function FindingCard({
  finding,
  findingIndex,
  citationIndexMap,
}: {
  finding: Finding;
  findingIndex: number;
  citationIndexMap: Map<string, number>;
}) {
  const evidenceParagraphs = splitReadableParagraphs(
    finding.evidence_summary,
    420,
  );

  return (
    <article
      className={`report-finding ${findingAccentClass(finding.confidence)}`}
    >
      <div className="report-finding-header">
        <span className="report-finding-index">Finding {findingIndex}</span>
        <span
          className={`fv-confidence-badge ${confidenceClass(finding.confidence)}`}
        >
          {finding.confidence} confidence
        </span>
      </div>
      <p className="report-finding-claim">{finding.claim}</p>
      {evidenceParagraphs.length > 0 && (
        <div className="report-finding-evidence">
          {evidenceParagraphs.map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-2" : undefined}>
              {paragraph}
              {index === evidenceParagraphs.length - 1 && (
                <CitationRefs
                  citations={finding.citations}
                  citationIndexMap={citationIndexMap}
                />
              )}
            </p>
          ))}
        </div>
      )}
      {finding.confidence_rationale && (
        <p className="mt-2 text-xs leading-relaxed text-[var(--fv-text-muted)]">
          {finding.confidence_rationale}
        </p>
      )}
    </article>
  );
}

export interface ReportCanvasProps {
  experimentId: string;
  projectName?: string;
  onClose?: () => void;
  /** Embedded in experiment page — no chrome header with close. */
  embedded?: boolean;
  mobile?: boolean;
}

export function ReportCanvas({
  experimentId,
  projectName = "Validation report",
  onClose,
  embedded = false,
  mobile = false,
}: ReportCanvasProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getValidationReport(experimentId);
        if (!cancelled) {
          setReport(data);
          const firstQuestionId = data.questions_and_findings[0]?.question_id;
          setExpandedQuestions(
            firstQuestionId ? new Set([firstQuestionId]) : new Set(),
          );
        }
      } catch {
        if (!cancelled) {
          setError("Could not load the validation report.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (fullscreen) {
        setFullscreen(false);
        return;
      }
      onClose?.();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, fullscreen]);

  useEffect(() => {
    if (!fullscreen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [fullscreen]);

  const citations = report ? collectAllCitations(report) : [];
  const citationIndexMap = buildCitationIndexMap(citations);
  const reportScores = report ? resolveReportScores(report) : null;
  const showRecommendation =
    report && report.overall_recommendation !== "too_vague_to_recommend";

  const sectionLinks = useMemo(() => {
    if (!report) return [];
    const links: { href: string; label: string }[] = [];
    if (
      report.overall_recommendation !== "too_vague_to_recommend" &&
      report.recommendation_rationale
    ) {
      links.push({ href: "#report-recommendation", label: "Recommendation" });
    }
    links.push(
      { href: "#report-scores", label: "Scores" },
      { href: "#report-summary", label: "Summary" },
      { href: "#report-findings", label: "Findings" },
    );
    if (report.competitors.length > 0) {
      links.push({ href: "#report-competitors", label: "Competitors" });
    }
    if (
      report.market_signals ||
      report.distribution_signals ||
      report.regulatory_signals
    ) {
      links.push({ href: "#report-market", label: "Market" });
    }
    if (report.risks_assessment) {
      links.push({ href: "#report-risks", label: "Risks" });
    }
    if (citations.length > 0) {
      links.push({ href: "#report-sources", label: "Sources" });
    }
    return links;
  }, [report, citations.length]);

  const allQuestionsExpanded =
    report !== null &&
    report.questions_and_findings.length > 0 &&
    report.questions_and_findings.every((qf) =>
      expandedQuestions.has(qf.question_id),
    );

  function toggleQuestion(qid: string) {
    setExpandedQuestions((prev) => {
      const next = new Set(prev);
      if (next.has(qid)) next.delete(qid);
      else next.add(qid);
      return next;
    });
  }

  function toggleAllQuestions() {
    if (!report) return;
    if (allQuestionsExpanded) {
      setExpandedQuestions(new Set());
      return;
    }
    setExpandedQuestions(
      new Set(report.questions_and_findings.map((qf) => qf.question_id)),
    );
  }

  const showOverlayHeader = !embedded || fullscreen;
  const showEmbeddedToolbar = embedded && !fullscreen && report && !loading;
  const findingCount = report ? countFindings(report) : 0;
  const questionCount = report?.questions_and_findings.length ?? 0;

  return (
    <div
      className={`flex min-h-0 flex-col bg-[var(--fv-bg)] ${
        fullscreen ? "fixed inset-0 z-[80] h-dvh max-h-dvh" : "h-full"
      }`}
    >
      {showEmbeddedToolbar && (
        <div className="flex shrink-0 items-center justify-end gap-2 border-b border-[var(--fv-border)] bg-[var(--fv-surface)]/80 px-4 py-2 backdrop-blur-sm">
          <ValidationReportExportMenu
            report={report}
            projectName={projectName}
            variant="ghost"
          />
          <button
            type="button"
            onClick={() => setFullscreen(true)}
            className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px]"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            Full screen
          </button>
        </div>
      )}

      {showOverlayHeader && (
        <header className="sticky top-0 z-10 flex shrink-0 items-center justify-between gap-3 border-b border-[var(--fv-border)] bg-[var(--fv-bg)]/95 px-4 py-3 backdrop-blur-sm sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {mobile && onClose && !fullscreen && (
              <button
                type="button"
                onClick={onClose}
                className="fv-icon-btn shrink-0 lg:hidden"
                aria-label="Back"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <FileText className="h-5 w-5 shrink-0 text-[var(--fv-accent)]" />
            <h1 className="truncate text-base font-semibold text-[var(--fv-text)]">
              Validation Report
            </h1>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {report && (
              <ValidationReportExportMenu
                report={report}
                projectName={projectName}
                variant="ghost"
              />
            )}
            {fullscreen ? (
              <button
                type="button"
                onClick={() => setFullscreen(false)}
                className="fv-btn-ghost inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] sm:px-3"
                aria-label="Exit full screen"
              >
                <Minimize2 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Exit full screen</span>
              </button>
            ) : embedded ? null : (
              <button
                type="button"
                onClick={() => setFullscreen(true)}
                className="fv-icon-btn"
                aria-label="View full screen"
                title="View full screen"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
            )}
            {onClose && !fullscreen && (
              <button
                type="button"
                onClick={onClose}
                className="fv-icon-btn shrink-0"
                aria-label="Close report"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-3 py-4 sm:px-5 sm:py-6">
          {loading && <LoadingState label="Loading validation report…" />}

          {error && !loading && <ErrorBanner message={error} />}

          {report && !loading && (
            <article className="report-canvas-article">
              <header className="report-masthead">
                <p className="report-masthead-eyebrow">Validation report</p>
                <h1 className="report-masthead-title">{projectName}</h1>
                {showRecommendation && (
                  <div className="mt-4">
                    <span
                      className={`report-recommendation-badge ${recommendationBadgeClass(
                        report.overall_recommendation,
                      )}`}
                    >
                      {formatRecommendation(report.overall_recommendation)}
                    </span>
                  </div>
                )}
                <div className="report-stats">
                  <span className="report-stat-pill">
                    <strong>{questionCount}</strong> research questions
                  </span>
                  <span className="report-stat-pill">
                    <strong>{findingCount}</strong> findings
                  </span>
                  <span className="report-stat-pill">
                    <strong>{citations.length}</strong> sources
                  </span>
                </div>
              </header>

              {reportScores && report && (
                <ReportScoreSection
                  report={report}
                  sections={reportScores.sections}
                  overall={reportScores.overall}
                  derived={reportScores.derived}
                />
              )}

              {sectionLinks.length > 0 && (
                <nav
                  className="report-section-nav"
                  aria-label="Report sections"
                >
                  <div className="report-section-nav-inner">
                    {sectionLinks.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        className="report-section-link"
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                </nav>
              )}

              {showRecommendation && report.recommendation_rationale && (
                <section
                  id="report-recommendation"
                  className="report-block"
                  aria-labelledby="report-recommendation-heading"
                >
                  <h2
                    id="report-recommendation-heading"
                    className="report-block-title"
                  >
                    <span className="report-block-icon">
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    Recommendation
                  </h2>
                  <div className="report-card report-card-accent">
                    <ReadableProse text={report.recommendation_rationale} />
                  </div>
                </section>
              )}

              <section
                id="report-summary"
                className="report-block"
                aria-labelledby="report-summary-heading"
              >
                <h2 id="report-summary-heading" className="report-block-title">
                  <span className="report-block-icon">
                    <BookOpen className="h-4 w-4" />
                  </span>
                  Executive summary
                </h2>
                <div className="report-card">
                  <ReadableProse text={report.executive_summary} />
                </div>
              </section>

              <section
                id="report-findings"
                className="report-block"
                aria-labelledby="report-findings-heading"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2
                    id="report-findings-heading"
                    className="report-block-title !mb-0"
                  >
                    <span className="report-block-icon">
                      <FileText className="h-4 w-4" />
                    </span>
                    Research findings
                  </h2>
                  {questionCount > 1 && (
                    <button
                      type="button"
                      onClick={toggleAllQuestions}
                      className="fv-btn-ghost px-2.5 py-1 text-[11px]"
                    >
                      {allQuestionsExpanded ? "Collapse all" : "Expand all"}
                    </button>
                  )}
                </div>

                <div className="space-y-3">
                  {report.questions_and_findings.map((qf, qIndex) => {
                    const expanded = expandedQuestions.has(qf.question_id);
                    const displayIndex = questionDisplayIndex(
                      qf.question_id,
                      qIndex + 1,
                    );
                    return (
                      <div key={qf.question_id} className="report-question">
                        <button
                          type="button"
                          onClick={() => toggleQuestion(qf.question_id)}
                          className="report-question-trigger"
                          aria-expanded={expanded}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="report-question-index">
                                {displayIndex}
                              </span>
                              <span className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
                                Research question
                              </span>
                              <span className="text-[11px] text-[var(--fv-text-dim)]">
                                · {qf.findings.length} finding
                                {qf.findings.length === 1 ? "" : "s"}
                              </span>
                              <span className="report-question-score" title="Question score">
                                {resolveQuestionScore(qf)}
                              </span>
                            </div>
                            <p className="report-question-title">{qf.question}</p>
                          </div>
                          <ChevronDown
                            className={`h-5 w-5 shrink-0 text-[var(--fv-text-muted)] transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {expanded && (
                          <div className="report-question-body space-y-3">
                            {qf.findings.map((finding, fIndex) => (
                              <FindingCard
                                key={`${finding.question_id}-${finding.claim.slice(0, 40)}`}
                                finding={finding}
                                findingIndex={fIndex + 1}
                                citationIndexMap={citationIndexMap}
                              />
                            ))}
                            {qf.evidence_gap && (
                              <div className="report-evidence-gap">
                                <strong>Evidence gap: </strong>
                                {qf.evidence_gap}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>

              {report.competitors.length > 0 && (
                <section
                  id="report-competitors"
                  className="report-block"
                  aria-labelledby="report-competitors-heading"
                >
                  <h2
                    id="report-competitors-heading"
                    className="report-block-title"
                  >
                    <span className="report-block-icon">
                      <Building2 className="h-4 w-4" />
                    </span>
                    Competitors
                  </h2>
                  <div className="report-competitor-grid">
                    {report.competitors.map((comp) => (
                      <div key={comp.name} className="report-competitor-card">
                        <h3 className="report-competitor-name">{comp.name}</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(comp.description, 320).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                        {comp.positioning_vs_idea && (
                          <p className="mt-3 text-xs leading-relaxed text-[var(--fv-text-muted)]">
                            <span className="font-medium text-[var(--fv-text-soft)]">
                              vs. your idea:{" "}
                            </span>
                            {comp.positioning_vs_idea}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {(report.market_signals ||
                report.distribution_signals ||
                report.regulatory_signals) && (
                <section
                  id="report-market"
                  className="report-block"
                  aria-labelledby="report-market-heading"
                >
                  <h2 id="report-market-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    Market signals
                  </h2>
                  <div className="report-card">
                    {report.market_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Market overview</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(report.market_signals).map(
                            (paragraph, index) => (
                              <p key={index}>{paragraph}</p>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                    {report.distribution_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Distribution</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(
                            report.distribution_signals,
                          ).map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    {report.regulatory_signals && (
                      <div className="report-signal-block">
                        <h3 className="report-signal-label">Regulatory</h3>
                        <div className="report-prose mt-2 text-sm">
                          {splitReadableParagraphs(
                            report.regulatory_signals,
                          ).map((paragraph, index) => (
                            <p key={index}>{paragraph}</p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {report.risks_assessment && (
                <section
                  id="report-risks"
                  className="report-block"
                  aria-labelledby="report-risks-heading"
                >
                  <h2 id="report-risks-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <AlertTriangle className="h-4 w-4" />
                    </span>
                    Risk assessment
                  </h2>
                  <div className="report-card border-[color-mix(in_srgb,var(--fv-warning)_22%,transparent)]">
                    <RiskAssessmentContent text={report.risks_assessment} />
                  </div>
                </section>
              )}

              {report.research_limitations && (
                <section className="report-block">
                  <h2 className="report-block-title">
                    <span className="report-block-icon">
                      <AlertTriangle className="h-4 w-4" />
                    </span>
                    Research limitations
                  </h2>
                  <div className="report-card">
                    <ReadableProse text={report.research_limitations} />
                  </div>
                </section>
              )}

              {citations.length > 0 && (
                <section
                  id="report-sources"
                  className="report-block"
                  aria-labelledby="report-sources-heading"
                >
                  <h2 id="report-sources-heading" className="report-block-title">
                    <span className="report-block-icon">
                      <ExternalLink className="h-4 w-4" />
                    </span>
                    Sources ({citations.length})
                  </h2>
                  <ol className="report-source-list">
                    {citations.map((citation, index) => (
                      <li
                        key={`${citation.url}-${index}`}
                        id={`citation-${index + 1}`}
                        className="report-source-item"
                      >
                        <span className="report-source-num">{index + 1}</span>
                        <div className="min-w-0">
                          <SafeCitationLink citation={citation} />
                          {citation.source_domain && (
                            <p className="mt-0.5 text-xs text-[var(--fv-text-muted)]">
                              {citation.source_domain}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              <p className="report-footer-note">
                Generated by Fivvle research engine · Rubric{" "}
                {report.rubric_version_used}
              </p>
            </article>
          )}
        </div>
      </div>
    </div>
  );
}
```

### `components/research/ReportScoreSection.tsx`

```typescript
"use client";

import { useMemo, useState } from "react";
import { ChevronRight, X } from "lucide-react";
import type { SectionScore, ValidationReport } from "@/lib/types";
import {
  buildOverallScoreDetail,
  buildSectionScoreDetails,
  type OverallScoreDetail,
  type ScoreSelectionId,
  type SectionScoreDetail,
} from "@/lib/validation-report-score-details";
import { scoreTone } from "@/lib/validation-report-scores";
import "./report-score-section.css";

interface ReportScoreSectionProps {
  report: ValidationReport;
  sections: SectionScore[];
  overall: number;
  derived?: boolean;
}

function ScoreBar({
  score,
  size = "md",
  label,
}: {
  score: number;
  size?: "md" | "lg";
  label: string;
}) {
  const tone = scoreTone(score);
  return (
    <div className="report-score-bar-wrap">
      <div
        className={`report-score-bar-track report-score-bar-${size}`}
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${score} out of 100`}
      >
        <div
          className={`report-score-bar-fill report-score-fill-${tone}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function BulletList({
  items,
  variant,
}: {
  items: string[];
  variant: "pro" | "con";
}) {
  if (items.length === 0) {
    return (
      <p className="report-score-detail-empty">
        {variant === "pro" ? "No clear positives surfaced." : "No major caveats noted."}
      </p>
    );
  }
  return (
    <ul className={`report-score-detail-list report-score-detail-${variant}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function ScoreDetailPanel({
  detail,
  onClose,
}: {
  detail: SectionScoreDetail | OverallScoreDetail;
  onClose: () => void;
}) {
  const id = "id" in detail ? detail.id : detail.section_id;
  const tone = scoreTone(detail.score);

  return (
    <div
      className="report-score-detail"
      role="region"
      aria-labelledby={`score-detail-title-${id}`}
    >
      <div className="report-score-detail-header">
        <div className="min-w-0 flex-1">
          <p className="report-score-detail-eyebrow">Score breakdown</p>
          <h3
            id={`score-detail-title-${id}`}
            className="report-score-detail-title"
          >
            {detail.label}
          </h3>
        </div>
        <span className={`report-score-detail-value report-score-tone-${tone}`}>
          {detail.score}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="report-score-detail-close"
          aria-label="Close score details"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <ScoreBar score={detail.score} label={detail.label} />

      <div className="report-score-detail-body">
        <div className="report-score-detail-block">
          <p className="report-score-detail-label">Why this score</p>
          <p className="report-score-detail-text">{detail.rationale}</p>
        </div>

        <div className="report-score-detail-columns">
          <div className="report-score-detail-block">
            <p className="report-score-detail-label report-score-detail-label-pro">
              Supporting signals
            </p>
            <BulletList items={detail.pros} variant="pro" />
          </div>
          <div className="report-score-detail-block">
            <p className="report-score-detail-label report-score-detail-label-con">
              Caveats & gaps
            </p>
            <BulletList items={detail.cons} variant="con" />
          </div>
        </div>

        <div className="report-score-detail-block">
          <p className="report-score-detail-label">Context from report</p>
          <p className="report-score-detail-context">{detail.context}</p>
        </div>
      </div>
    </div>
  );
}

function SectionScoreCard({
  detail,
  selected,
  onSelect,
}: {
  detail: SectionScoreDetail;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-expanded={selected}
      aria-controls={`score-detail-${detail.section_id}`}
      className={`report-score-card report-score-card-btn${selected ? " report-score-card-selected" : ""}`}
    >
      <div className="report-score-card-header">
        <p className="report-score-card-label">{detail.label}</p>
        <span className="report-score-card-meta">
          <span
            className={`report-score-value report-score-tone-${scoreTone(detail.score)}`}
          >
            {detail.score}
          </span>
          <ChevronRight
            className={`report-score-chevron${selected ? " report-score-chevron-open" : ""}`}
            aria-hidden
          />
        </span>
      </div>
      <ScoreBar score={detail.score} label={detail.label} />
    </button>
  );
}

export function ReportScoreSection({
  report,
  sections,
  overall,
  derived = false,
}: ReportScoreSectionProps) {
  const [selectedId, setSelectedId] = useState<ScoreSelectionId | null>(null);

  const sectionDetails = useMemo(
    () => buildSectionScoreDetails(report, sections),
    [report, sections],
  );

  const overallDetail = useMemo(
    () => buildOverallScoreDetail(report, overall),
    [report, overall],
  );

  const activeDetail: SectionScoreDetail | OverallScoreDetail | null =
    selectedId === "overall"
      ? overallDetail
      : selectedId
        ? sectionDetails.find((d) => d.section_id === selectedId) ?? null
        : null;

  function toggleSelection(id: ScoreSelectionId) {
    setSelectedId((current) => (current === id ? null : id));
  }

  return (
    <section
      id="report-scores"
      className="report-score-panel"
      aria-labelledby="report-scores-heading"
    >
      <div className="report-score-panel-header">
        <h2 id="report-scores-heading" className="report-score-panel-title">
          Validation scores
        </h2>
        <span className="report-score-derived-note">
          {derived ? "Estimated from evidence · " : ""}
          Tap a score for details
        </span>
      </div>

      <div className="report-score-grid">
        {sectionDetails.map((detail) => (
          <SectionScoreCard
            key={detail.section_id}
            detail={detail}
            selected={selectedId === detail.section_id}
            onSelect={() => toggleSelection(detail.section_id)}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={() => toggleSelection("overall")}
        aria-expanded={selectedId === "overall"}
        className={`report-score-overall report-score-overall-btn${
          selectedId === "overall" ? " report-score-card-selected" : ""
        }`}
      >
        <div className="report-score-overall-header">
          <p className="report-score-overall-label">Overall score</p>
          <span className="report-score-card-meta">
            <span
              className={`report-score-overall-value report-score-tone-${scoreTone(overall)}`}
            >
              {overall}
            </span>
            <ChevronRight
              className={`report-score-chevron${selectedId === "overall" ? " report-score-chevron-open" : ""}`}
              aria-hidden
            />
          </span>
        </div>
        <ScoreBar score={overall} size="lg" label="Overall validation score" />
      </button>

      {activeDetail && (
        <div id={`score-detail-${selectedId}`}>
          <ScoreDetailPanel
            detail={activeDetail}
            onClose={() => setSelectedId(null)}
          />
        </div>
      )}
    </section>
  );
}
```

### `components/research/ValidationReportExportMenu.tsx`

```typescript
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
```

### `components/research/report-canvas.css`

```css
/* Validation report — readable editorial layout */

.report-canvas-article {
  --report-prose-width: 42rem;
  color: var(--fv-text);
}

.report-masthead {
  position: relative;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 22%, transparent);
  border-radius: 1rem;
  background:
    radial-gradient(
      120% 140% at 100% 0%,
      color-mix(in srgb, var(--fv-accent) 14%, transparent),
      transparent 55%
    ),
    linear-gradient(
      165deg,
      color-mix(in srgb, var(--fv-surface-2) 92%, transparent),
      var(--fv-surface)
    );
  padding: 1.25rem 1.25rem 1.5rem;
}

@media (min-width: 640px) {
  .report-masthead {
    padding: 1.5rem 1.75rem 1.75rem;
  }
}

.report-masthead-eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-masthead-title {
  margin-top: 0.35rem;
  font-size: 1.35rem;
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--fv-text);
}

@media (min-width: 640px) {
  .report-masthead-title {
    font-size: 1.6rem;
  }
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

.report-stat-pill strong {
  font-weight: 650;
  color: var(--fv-text);
}

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

.report-section-nav {
  position: sticky;
  top: 0;
  z-index: 5;
  margin: 0 -0.25rem 1.25rem;
  padding: 0.5rem 0.25rem;
  background: color-mix(in srgb, var(--fv-bg) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--fv-border);
}

.report-section-nav-inner {
  display: flex;
  gap: 0.35rem;
  overflow-x: auto;
  padding-bottom: 0.15rem;
  scrollbar-width: none;
}

.report-section-nav-inner::-webkit-scrollbar {
  display: none;
}

.report-section-link {
  flex-shrink: 0;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 0.35rem 0.75rem;
  font-size: 12px;
  font-weight: 500;
  color: var(--fv-text-muted);
  text-decoration: none;
  transition:
    color 0.15s,
    border-color 0.15s,
    background 0.15s;
}

.report-section-link:hover {
  color: var(--fv-text);
  border-color: var(--fv-border);
  background: color-mix(in srgb, white 4%, transparent);
}

.report-block {
  scroll-margin-top: 4.5rem;
  margin-bottom: 2rem;
}

.report-block-title {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 1rem;
  font-size: 1.05rem;
  font-weight: 650;
  letter-spacing: -0.02em;
  color: var(--fv-text);
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

.report-card {
  border: 1px solid var(--fv-border);
  border-radius: 0.875rem;
  background: var(--fv-surface);
  padding: 1.25rem 1.25rem 1.35rem;
}

.report-card-accent {
  border-color: color-mix(in srgb, var(--fv-accent) 28%, transparent);
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--fv-accent) 9%, transparent),
    var(--fv-surface) 45%
  );
}

.report-recommendation-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 0.625rem;
  padding: 0.4rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.report-prose {
  max-width: var(--report-prose-width);
  font-size: 0.9375rem;
  line-height: 1.72;
  color: var(--fv-text-soft);
}

.report-prose p + p {
  margin-top: 0.85em;
}

.report-question {
  overflow: hidden;
  border: 1px solid var(--fv-border);
  border-radius: 0.875rem;
  background: color-mix(in srgb, var(--fv-surface-2) 80%, transparent);
}

.report-question-trigger {
  display: flex;
  width: 100%;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.1rem;
  text-align: left;
  transition: background 0.15s;
}

.report-question-trigger:hover {
  background: color-mix(in srgb, white 3%, transparent);
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

.report-question-title {
  margin-top: 0.45rem;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.45;
  color: var(--fv-text);
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
}

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

.report-finding-high::before {
  background: var(--fv-success);
}

.report-finding-medium::before {
  background: var(--fv-warning);
}

.report-finding-low::before {
  background: var(--fv-text-dim);
}

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

.report-finding-claim {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.5;
  color: var(--fv-text);
}

.report-finding-evidence {
  margin-top: 0.65rem;
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--fv-text-soft);
}

.report-cite-ref {
  margin-left: 0.15rem;
  font-size: 10px;
  font-weight: 600;
  color: var(--fv-accent);
  text-decoration: none;
  vertical-align: super;
}

.report-cite-ref:hover {
  text-decoration: underline;
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

.report-evidence-gap strong {
  color: var(--fv-warning);
}

.report-competitor-grid {
  display: grid;
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .report-competitor-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.report-competitor-card {
  border: 1px solid var(--fv-border);
  border-radius: 0.75rem;
  background: var(--fv-surface);
  padding: 1rem;
}

.report-competitor-name {
  font-size: 0.95rem;
  font-weight: 650;
  color: var(--fv-text);
}

.report-signal-block + .report-signal-block {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--fv-border);
}

.report-signal-label {
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-source-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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

.report-footer-note {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--fv-border);
  font-size: 11px;
  color: var(--fv-text-dim);
}

.report-risk-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.report-risk-item {
  border-radius: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--fv-warning) 22%, transparent);
  background: color-mix(in srgb, var(--fv-warning) 4%, var(--fv-surface));
  padding: 1rem 1.05rem 1.1rem;
}

.report-risk-header {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

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

.report-risk-heading {
  min-width: 0;
  flex: 1;
}

.report-risk-title {
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.4;
  color: var(--fv-text);
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

.report-risk-body p + p {
  margin-top: 0.65em;
}

.report-risk-preamble {
  margin-bottom: 0.85rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--fv-border);
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--fv-text-soft);
}
```

### `components/research/report-score-section.css`

```css
/* Validation score panel — 2-up section cards + overall bar */
/* Keep in sync with lib/report-score-section-export-css.ts for HTML downloads. */

.report-score-panel {
  border: 1px solid var(--fv-border);
  border-radius: 1rem;
  background: var(--fv-surface);
  padding: 1rem;
}

.report-canvas-article .report-score-panel {
  margin-top: 1.25rem;
}

@media (min-width: 640px) {
  .report-score-panel {
    padding: 1.15rem 1.25rem 1.25rem;
  }
}

.report-score-panel-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.85rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--fv-border);
}

.report-score-panel-title {
  font-size: 0.8rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fv-text-soft);
}

.report-score-derived-note {
  font-size: 10px;
  font-weight: 500;
  color: var(--fv-text-muted);
}

.report-score-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem;
}

@media (min-width: 520px) {
  .report-score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }
}

.report-score-card {
  border: 1px solid var(--fv-border);
  border-radius: 0.75rem;
  background: color-mix(in srgb, white 2%, transparent);
  padding: 0.75rem 0.85rem;
}

.report-score-card-btn,
.report-score-overall-btn {
  display: block;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.report-score-card-btn:hover,
.report-score-overall-btn:hover {
  border-color: color-mix(in srgb, var(--fv-accent) 35%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-accent) 4%, transparent);
}

.report-score-card-selected {
  border-color: color-mix(in srgb, var(--fv-accent) 45%, var(--fv-border));
  background: color-mix(in srgb, var(--fv-accent) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--fv-accent) 20%, transparent);
}

.report-score-card-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.report-score-chevron {
  width: 0.95rem;
  height: 0.95rem;
  color: var(--fv-text-muted);
  transition: transform 0.2s ease;
}

.report-score-chevron-open {
  transform: rotate(90deg);
  color: var(--fv-accent);
}

.report-score-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.55rem;
}

.report-score-card-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--fv-text);
}

.report-score-value {
  font-size: 0.95rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.report-score-overall {
  margin-top: 0.85rem;
  border: 1px solid color-mix(in srgb, var(--fv-accent) 25%, transparent);
  border-radius: 0.85rem;
  background: color-mix(in srgb, var(--fv-accent) 6%, transparent);
  padding: 0.85rem 1rem 1rem;
}

.report-score-overall-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
}

.report-score-overall-label {
  font-size: 0.85rem;
  font-weight: 650;
  color: var(--fv-text);
}

.report-score-overall-value {
  font-size: 1.35rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.report-score-bar-wrap {
  width: 100%;
}

.report-score-bar-track {
  position: relative;
  overflow: hidden;
  width: 100%;
  border-radius: 999px;
  background: color-mix(in srgb, var(--fv-text) 8%, transparent);
}

.report-score-bar-md {
  height: 7px;
}

.report-score-bar-lg {
  height: 11px;
}

.report-score-bar-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.35s ease;
}

.report-score-fill-strong {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--fv-success) 85%, transparent),
    var(--fv-success)
  );
}

.report-score-fill-mixed {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--fv-warning) 75%, transparent),
    var(--fv-warning)
  );
}

.report-score-fill-weak {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--fv-text-muted) 70%, transparent),
    color-mix(in srgb, var(--fv-text-soft) 90%, transparent)
  );
}

.report-score-tone-strong {
  color: var(--fv-success);
}

.report-score-tone-mixed {
  color: var(--fv-warning);
}

.report-score-tone-weak {
  color: var(--fv-text-muted);
}

.report-score-detail {
  margin-top: 0.85rem;
  border: 1px solid var(--fv-border);
  border-radius: 0.85rem;
  background: var(--fv-surface-2);
  padding: 1rem;
  animation: report-score-detail-in 0.2s ease;
}

@keyframes report-score-detail-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.report-score-detail-header {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.report-score-detail-eyebrow {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
}

.report-score-detail-title {
  margin-top: 0.15rem;
  font-size: 1rem;
  font-weight: 650;
  color: var(--fv-text);
}

.report-score-detail-value {
  font-size: 1.25rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.report-score-detail-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 0.45rem;
  padding: 0.25rem;
  background: transparent;
  color: var(--fv-text-muted);
  cursor: pointer;
}

.report-score-detail-close:hover {
  background: color-mix(in srgb, white 6%, transparent);
  color: var(--fv-text);
}

.report-score-detail-body {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.report-score-detail-block {
  min-width: 0;
}

.report-score-detail-label {
  font-size: 10px;
  font-weight: 650;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fv-text-muted);
  margin-bottom: 0.4rem;
}

.report-score-detail-label-pro {
  color: var(--fv-success);
}

.report-score-detail-label-con {
  color: var(--fv-warning);
}

.report-score-detail-text,
.report-score-detail-context {
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--fv-text-soft);
}

.report-score-detail-context {
  white-space: pre-wrap;
  border-radius: 0.65rem;
  border: 1px solid var(--fv-border);
  background: color-mix(in srgb, white 3%, transparent);
  padding: 0.65rem 0.75rem;
  font-size: 0.8125rem;
}

.report-score-detail-columns {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.85rem;
}

@media (min-width: 560px) {
  .report-score-detail-columns {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.report-score-detail-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--fv-text-soft);
}

.report-score-detail-list li + li {
  margin-top: 0.35rem;
}

.report-score-detail-pro li::marker {
  color: var(--fv-success);
}

.report-score-detail-con li::marker {
  color: var(--fv-warning);
}

.report-score-detail-empty {
  font-size: 0.8125rem;
  color: var(--fv-text-muted);
  font-style: italic;
}
```

### `lib/report-text.ts`

```typescript
export interface ParsedRiskItem {
  number: number;
  title: string;
  body: string;
  verdict: string | null;
}

export interface ParsedRiskAssessment {
  items: ParsedRiskItem[];
  preamble: string | null;
  isStructured: boolean;
}

const NUMBERED_RISK_MARKER =
  /Risk\s+(\d+)\s*[—–-]\s*([^:]+):\s*/gi;

const NARRATIVE_RISK_MARKER =
  /The\s+(.+?)\s+risk\s+\(([^)]+)\)\s+is\s+([^:]+):\s*/gi;

function cleanRiskBody(body: string): string {
  return body
    .trim()
    .replace(/^["']\s*/, "")
    .replace(/\s*["']$/, "")
    .replace(/^[,;:]+\s*/, "")
    .trim();
}

function splitRiskVerdict(body: string): { verdict: string | null; detail: string } {
  const trimmed = cleanRiskBody(body);
  const dotIndex = trimmed.search(/[.!?]/);
  if (dotIndex === -1) {
    return { verdict: null, detail: trimmed };
  }

  const firstSentence = trimmed.slice(0, dotIndex + 1).trim();
  const remainder = trimmed.slice(dotIndex + 1).trim();

  const looksLikeVerdict =
    firstSentence.length <= 96 &&
    /^(Concerning|Mixed|Partially|Critically|High |Low |Unvalidated|Confirmed|Under-evidenced|Potentially|Substantially|Not |No direct)/i.test(
      firstSentence,
    );

  if (!looksLikeVerdict) {
    return { verdict: null, detail: trimmed };
  }

  return {
    verdict: firstSentence.replace(/\.$/, ""),
    detail: remainder,
  };
}

function parseNumberedRisks(text: string): ParsedRiskItem[] {
  const matches: {
    index: number;
    number: number;
    title: string;
    markerLength: number;
  }[] = [];

  for (const match of text.matchAll(NUMBERED_RISK_MARKER)) {
    if (match.index === undefined) continue;
    matches.push({
      index: match.index,
      number: Number.parseInt(match[1], 10),
      title: match[2].trim(),
      markerLength: match[0].length,
    });
  }

  if (matches.length === 0) {
    return [];
  }

  return matches.map((current, index) => {
    const bodyStart = current.index + current.markerLength;
    const bodyEnd =
      index + 1 < matches.length ? matches[index + 1].index : text.length;
    const rawBody = cleanRiskBody(text.slice(bodyStart, bodyEnd));
    const { verdict, detail } = splitRiskVerdict(rawBody);

    return {
      number: current.number,
      title: current.title,
      body: detail || rawBody,
      verdict,
    };
  });
}

function parseNarrativeRisks(text: string): ParsedRiskItem[] {
  const matches: {
    index: number;
    title: string;
    questionRefs: string;
    verdict: string;
    markerLength: number;
  }[] = [];

  for (const match of text.matchAll(NARRATIVE_RISK_MARKER)) {
    if (match.index === undefined) continue;
    matches.push({
      index: match.index,
      title: match[1].trim(),
      questionRefs: match[2].trim(),
      verdict: match[3].trim(),
      markerLength: match[0].length,
    });
  }

  if (matches.length < 2) {
    return [];
  }

  return matches.map((current, index) => {
    const bodyStart = current.index + current.markerLength;
    const bodyEnd =
      index + 1 < matches.length ? matches[index + 1].index : text.length;

    return {
      number: index + 1,
      title: `${current.title} (${current.questionRefs})`,
      body: cleanRiskBody(text.slice(bodyStart, bodyEnd)),
      verdict: current.verdict,
    };
  });
}

/** Parse synthesizer risk prose into discrete risk items when markers are present. */
export function parseRiskAssessment(text: string): ParsedRiskAssessment {
  const trimmed = text.trim();
  if (!trimmed) {
    return { items: [], preamble: null, isStructured: false };
  }

  const numberedMatches = [...trimmed.matchAll(NUMBERED_RISK_MARKER)];
  if (numberedMatches.length > 0) {
    const firstIndex = numberedMatches[0].index ?? 0;
    const preamble =
      firstIndex > 0 ? cleanRiskBody(trimmed.slice(0, firstIndex)) : null;

    return {
      items: parseNumberedRisks(trimmed),
      preamble: preamble || null,
      isStructured: true,
    };
  }

  const narrativeItems = parseNarrativeRisks(trimmed);
  if (narrativeItems.length > 0) {
    return {
      items: narrativeItems,
      preamble: null,
      isStructured: true,
    };
  }

  return { items: [], preamble: null, isStructured: false };
}

/** Split long report prose into shorter paragraphs for on-screen readability. */

export function splitReadableParagraphs(text: string, maxChars = 380): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  if (trimmed.length <= maxChars) {
    return [trimmed];
  }

  const sentenceBoundary = /(?<=[.!?])\s+(?=[A-Z("'\u201C\u2018])/g;
  const sentences = trimmed
    .split(sentenceBoundary)
    .map((s) => s.trim())
    .filter(Boolean);

  if (sentences.length === 0) {
    return [trimmed];
  }

  const paragraphs: string[] = [];
  let buffer = "";

  for (const sentence of sentences) {
    const candidate = buffer ? `${buffer} ${sentence}` : sentence;
    if (candidate.length > maxChars && buffer) {
      paragraphs.push(buffer);
      buffer = sentence;
    } else {
      buffer = candidate;
    }
  }

  if (buffer) {
    paragraphs.push(buffer);
  }

  return paragraphs.length > 0 ? paragraphs : [trimmed];
}

export function questionDisplayIndex(questionId: string, fallback: number): number {
  const match = questionId.match(/(\d+)/);
  if (match) return Number.parseInt(match[1], 10);
  return fallback;
}
```

### `lib/validation-report-export.ts`

```typescript
import {
  parseRiskAssessment,
  questionDisplayIndex,
  splitReadableParagraphs,
} from "./report-text";
import type {
  Citation,
  Finding,
  OverallRecommendation,
  ValidationReport,
} from "./types";
import {
  VALIDATION_REPORT_HTML_CSS,
  VALIDATION_REPORT_SCORE_HTML_CSS,
  VALIDATION_REPORT_SCORE_SCRIPT,
  VALIDATION_REPORT_THEME_SCRIPT,
} from "./validation-report-html-styles";
import { buildScorePanelHtml } from "./validation-report-score-html";
import { resolveQuestionScore, resolveReportScores } from "./validation-report-scores";

function slugifyFilename(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug.slice(0, 60) || "validation-report";
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(value: string): string {
  return escapeHtml(value);
}

function formatRecommendation(rec: OverallRecommendation): string {
  if (rec === "too_vague_to_recommend") return "Needs clarity";
  return rec.charAt(0).toUpperCase() + rec.slice(1);
}

function recommendationBadgeClass(rec: OverallRecommendation): string {
  switch (rec) {
    case "proceed":
      return "badge-proceed";
    case "iterate":
      return "badge-iterate";
    case "pivot":
      return "badge-pivot";
    case "kill":
      return "badge-kill";
    default:
      return "badge-iterate";
  }
}

function confidenceClass(confidence: string): string {
  if (confidence === "high") return "fv-confidence-high";
  if (confidence === "medium") return "fv-confidence-medium";
  return "fv-confidence-low";
}

function findingAccentClass(confidence: string): string {
  if (confidence === "high") return "report-finding-high";
  if (confidence === "medium") return "report-finding-medium";
  return "report-finding-low";
}

function isSafeHttpUrl(url: string): boolean {
  return url.startsWith("http://") || url.startsWith("https://");
}

function collectAllCitations(report: ValidationReport): Citation[] {
  const seen = new Set<string>();
  const citations: Citation[] = [];

  const add = (citation: Citation) => {
    const key = citation.url || citation.title;
    if (!seen.has(key)) {
      seen.add(key);
      citations.push(citation);
    }
  };

  for (const qf of report.questions_and_findings) {
    for (const finding of qf.findings) {
      for (const citation of finding.citations) {
        add(citation);
      }
    }
  }
  for (const comp of report.competitors) {
    for (const citation of comp.citations) {
      add(citation);
    }
  }

  return citations;
}

function buildCitationIndexMap(citations: Citation[]): Map<string, number> {
  const map = new Map<string, number>();
  citations.forEach((citation, index) => {
    map.set(citation.url || citation.title, index + 1);
  });
  return map;
}

function countFindings(report: ValidationReport): number {
  return report.questions_and_findings.reduce(
    (total, qf) => total + qf.findings.length,
    0,
  );
}

function proseHtml(text: string, maxChars = 380): string {
  const paragraphs = splitReadableParagraphs(text, maxChars);
  if (paragraphs.length === 0) return "";
  return `<div class="report-prose">${paragraphs
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("")}</div>`;
}

function citationRefsHtml(
  citations: Citation[],
  citationIndexMap: Map<string, number>,
): string {
  return citations
    .map((citation) => {
      const key = citation.url || citation.title;
      const index = citationIndexMap.get(key);
      if (!index) return "";
      return `<a href="#citation-${index}" class="report-cite-ref" title="${escapeAttr(citation.title)}">[${index}]</a>`;
    })
    .join("");
}

function findingHtml(
  finding: Finding,
  findingIndex: number,
  citationIndexMap: Map<string, number>,
): string {
  const evidenceParagraphs = splitReadableParagraphs(
    finding.evidence_summary,
    420,
  );

  const evidenceHtml =
    evidenceParagraphs.length > 0
      ? `<div class="report-finding-evidence">${evidenceParagraphs
          .map((paragraph, index) => {
            const refs =
              index === evidenceParagraphs.length - 1
                ? citationRefsHtml(finding.citations, citationIndexMap)
                : "";
            return `<p>${escapeHtml(paragraph)}${refs}</p>`;
          })
          .join("")}</div>`
      : "";

  const rationaleHtml = finding.confidence_rationale
    ? `<p class="report-finding-rationale">${escapeHtml(finding.confidence_rationale)}</p>`
    : "";

  return `<article class="report-finding ${findingAccentClass(finding.confidence)}">
  <div class="report-finding-header">
    <span class="report-finding-index">Finding ${findingIndex}</span>
    <span class="fv-confidence-badge ${confidenceClass(finding.confidence)}">${escapeHtml(finding.confidence)} confidence</span>
  </div>
  <p class="report-finding-claim">${escapeHtml(finding.claim)}</p>
  ${evidenceHtml}
  ${rationaleHtml}
</article>`;
}

function riskSectionHtml(text: string): string {
  const parsed = parseRiskAssessment(text);
  if (!parsed.isStructured) {
    return proseHtml(text);
  }

  const preambleHtml = parsed.preamble
    ? `<div class="report-risk-preamble">${splitReadableParagraphs(parsed.preamble, 420)
        .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
        .join("")}</div>`
    : "";

  const itemsHtml = parsed.items
    .map(
      (risk) => `<li class="report-risk-item">
  <div class="report-risk-header">
    <span class="report-risk-num">${risk.number}</span>
    <div>
      <h3 class="report-risk-title">${escapeHtml(risk.title)}</h3>
      ${risk.verdict ? `<span class="report-risk-verdict">${escapeHtml(risk.verdict)}</span>` : ""}
    </div>
  </div>
  ${
    risk.body
      ? `<div class="report-risk-body">${splitReadableParagraphs(risk.body, 420)
          .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
          .join("")}</div>`
      : ""
  }
</li>`,
    )
    .join("");

  return `${preambleHtml}<ol class="report-risk-list">${itemsHtml}</ol>`;
}

const ICONS = {
  trend: `<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`,
  book: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
  file: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  building: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>`,
  alert: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  link: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
} as const;

function sectionTitle(id: string, icon: string, label: string): string {
  return `<h2 id="${id}" class="report-block-title"><span class="report-block-icon">${icon}</span>${escapeHtml(label)}</h2>`;
}

function buildSectionNav(report: ValidationReport, citationCount: number): string {
  const links: { href: string; label: string }[] = [];

  if (
    report.overall_recommendation !== "too_vague_to_recommend" &&
    report.recommendation_rationale
  ) {
    links.push({ href: "#report-recommendation", label: "Recommendation" });
  }
  links.push(
    { href: "#report-scores", label: "Scores" },
    { href: "#report-summary", label: "Summary" },
    { href: "#report-findings", label: "Findings" },
  );
  if (report.competitors.length > 0) {
    links.push({ href: "#report-competitors", label: "Competitors" });
  }
  if (
    report.market_signals ||
    report.distribution_signals ||
    report.regulatory_signals
  ) {
    links.push({ href: "#report-market", label: "Market" });
  }
  if (report.risks_assessment) {
    links.push({ href: "#report-risks", label: "Risks" });
  }
  if (citationCount > 0) {
    links.push({ href: "#report-sources", label: "Sources" });
  }

  return `<nav class="report-section-nav" aria-label="Report sections">
  <div class="report-section-nav-inner">
    ${links
      .map(
        (link) =>
          `<a href="${link.href}" class="report-section-link">${escapeHtml(link.label)}</a>`,
      )
      .join("")}
  </div>
</nav>`;
}

export function buildValidationReportHtml(
  report: ValidationReport,
  projectName: string,
  initialTheme: "light" | "dark" = "dark",
): string {
  const citations = collectAllCitations(report);
  const citationIndexMap = buildCitationIndexMap(citations);
  const showRecommendation =
    report.overall_recommendation !== "too_vague_to_recommend";
  const questionCount = report.questions_and_findings.length;
  const findingCount = countFindings(report);
  const exportedAt = new Date().toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const recommendationSection =
    showRecommendation && report.recommendation_rationale
      ? `<section id="report-recommendation" class="report-block">
  ${sectionTitle("report-recommendation-heading", ICONS.trend, "Recommendation")}
  <div class="report-card report-card-accent">${proseHtml(report.recommendation_rationale)}</div>
</section>`
      : "";

  const findingsHtml = report.questions_and_findings
    .map((qf, qIndex) => {
      const displayIndex = questionDisplayIndex(qf.question_id, qIndex + 1);
      const qScore = resolveQuestionScore(qf);
      const findings = qf.findings
        .map((finding, fIndex) =>
          findingHtml(finding, fIndex + 1, citationIndexMap),
        )
        .join("");
      const evidenceGapHtml = qf.evidence_gap
        ? `<div class="report-evidence-gap"><strong>Evidence gap: </strong>${escapeHtml(qf.evidence_gap)}</div>`
        : "";

      return `<div class="report-question">
  <div class="report-question-header">
    <div class="report-question-meta">
      <span class="report-question-index">${displayIndex}</span>
      <span class="report-question-label">Research question</span>
      <span class="report-question-count">· ${qf.findings.length} finding${qf.findings.length === 1 ? "" : "s"}</span>
      <span class="report-question-score" title="Question score">${qScore}</span>
    </div>
    <p class="report-question-title">${escapeHtml(qf.question)}</p>
  </div>
  <div class="report-question-body">
    ${findings}
    ${evidenceGapHtml}
  </div>
</div>`;
    })
    .join("");

  const competitorsHtml =
    report.competitors.length > 0
      ? `<section id="report-competitors" class="report-block">
  ${sectionTitle("report-competitors-heading", ICONS.building, "Competitors")}
  <div class="report-competitor-grid">
    ${report.competitors
      .map(
        (comp) => `<div class="report-competitor-card">
      <h3 class="report-competitor-name">${escapeHtml(comp.name)}</h3>
      ${proseHtml(comp.description, 320)}
      ${
        comp.positioning_vs_idea
          ? `<p class="report-competitor-vs"><strong>vs. your idea:</strong> ${escapeHtml(comp.positioning_vs_idea)}</p>`
          : ""
      }
    </div>`,
      )
      .join("")}
  </div>
</section>`
      : "";

  const marketSignals: string[] = [];
  if (report.market_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Market overview</h3>
  ${proseHtml(report.market_signals)}
</div>`);
  }
  if (report.distribution_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Distribution</h3>
  ${proseHtml(report.distribution_signals)}
</div>`);
  }
  if (report.regulatory_signals) {
    marketSignals.push(`<div class="report-signal-block">
  <h3 class="report-signal-label">Regulatory</h3>
  ${proseHtml(report.regulatory_signals)}
</div>`);
  }

  const marketHtml =
    marketSignals.length > 0
      ? `<section id="report-market" class="report-block">
  ${sectionTitle("report-market-heading", ICONS.trend, "Market signals")}
  <div class="report-card">${marketSignals.join("")}</div>
</section>`
      : "";

  const risksHtml = report.risks_assessment
    ? `<section id="report-risks" class="report-block">
  ${sectionTitle("report-risks-heading", ICONS.alert, "Risk assessment")}
  <div class="report-card report-card-warning-border">${riskSectionHtml(report.risks_assessment)}</div>
</section>`
    : "";

  const limitationsHtml = report.research_limitations
    ? `<section class="report-block">
  ${sectionTitle("report-limitations-heading", ICONS.alert, "Research limitations")}
  <div class="report-card">${proseHtml(report.research_limitations)}</div>
</section>`
    : "";

  const sourcesHtml =
    citations.length > 0
      ? `<section id="report-sources" class="report-block">
  ${sectionTitle("report-sources-heading", ICONS.link, `Sources (${citations.length})`)}
  <ol class="report-source-list">
    ${citations
      .map((citation, index) => {
        const title = citation.title || citation.url || "Source";
        const linkHtml = isSafeHttpUrl(citation.url)
          ? `<a class="report-source-link" href="${escapeAttr(citation.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>`
          : `<span>${escapeHtml(title)}</span>`;
        const domainHtml = citation.source_domain
          ? `<p class="report-source-domain">${escapeHtml(citation.source_domain)}</p>`
          : "";
        return `<li id="citation-${index + 1}" class="report-source-item">
      <span class="report-source-num">${index + 1}</span>
      <div>${linkHtml}${domainHtml}</div>
    </li>`;
      })
      .join("")}
  </ol>
</section>`
      : "";

  const badgeHtml = showRecommendation
    ? `<div style="margin-top:1rem"><span class="report-recommendation-badge ${recommendationBadgeClass(report.overall_recommendation)}">${escapeHtml(formatRecommendation(report.overall_recommendation))}</span></div>`
    : "";

  const lightActive = initialTheme === "light";
  const themeBootScript = `(function(){try{var t=localStorage.getItem("fivvle-report-theme");if(t!=="light"&&t!=="dark"){t="${initialTheme}";}document.documentElement.setAttribute("data-theme",t==="light"?"light":"dark");}catch(e){document.documentElement.setAttribute("data-theme","${initialTheme}");}})();`;

  return `<!DOCTYPE html>
<html lang="en" data-theme="${initialTheme}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(projectName)} — Validation Report</title>
  <script>${themeBootScript}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>${VALIDATION_REPORT_HTML_CSS}${VALIDATION_REPORT_SCORE_HTML_CSS}</style>
</head>
<body>
  <div class="report-page">
    <div class="report-export-header">
      <span class="report-export-brand">Fivvle</span>
      <div class="report-export-header-actions">
        <div class="report-theme-toggle" role="group" aria-label="Report theme">
          <button type="button" class="report-theme-btn${lightActive ? " report-theme-btn-active" : ""}" data-theme-btn="light" aria-pressed="${lightActive ? "true" : "false"}">Light</button>
          <button type="button" class="report-theme-btn${lightActive ? "" : " report-theme-btn-active"}" data-theme-btn="dark" aria-pressed="${lightActive ? "false" : "true"}">Dark</button>
        </div>
        <span class="report-export-date">Exported ${escapeHtml(exportedAt)}</span>
      </div>
    </div>
    <article class="report-canvas-article">
      <header class="report-masthead">
        <p class="report-masthead-eyebrow">Validation report</p>
        <h1 class="report-masthead-title">${escapeHtml(projectName)}</h1>
        ${badgeHtml}
        <div class="report-stats">
          <span class="report-stat-pill"><strong>${questionCount}</strong> research questions</span>
          <span class="report-stat-pill"><strong>${findingCount}</strong> findings</span>
          <span class="report-stat-pill"><strong>${citations.length}</strong> sources</span>
        </div>
      </header>

      ${buildScorePanelHtml(report)}

      ${buildSectionNav(report, citations.length)}

      ${recommendationSection}

      <section id="report-summary" class="report-block">
        ${sectionTitle("report-summary-heading", ICONS.book, "Executive summary")}
        <div class="report-card">${proseHtml(report.executive_summary)}</div>
      </section>

      <section id="report-findings" class="report-block">
        ${sectionTitle("report-findings-heading", ICONS.file, "Research findings")}
        ${findingsHtml}
      </section>

      ${competitorsHtml}
      ${marketHtml}
      ${risksHtml}
      ${limitationsHtml}
      ${sourcesHtml}

      <p class="report-footer-note">Generated by Fivvle research engine · Rubric ${escapeHtml(report.rubric_version_used)}</p>
    </article>
  </div>
  <script>${VALIDATION_REPORT_THEME_SCRIPT}</script>
  <script>${VALIDATION_REPORT_SCORE_SCRIPT}</script>
</body>
</html>`;
}

function downloadHtmlFile(html: string, filename: string): void {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function resolveDownloadTheme(): "light" | "dark" {
  if (typeof document === "undefined") return "dark";
  const theme = document.documentElement.getAttribute("data-theme");
  return theme === "light" ? "light" : "dark";
}

export function downloadValidationReportHtml(
  report: ValidationReport,
  projectName = "validation-report",
): void {
  const html = buildValidationReportHtml(
    report,
    projectName,
    resolveDownloadTheme(),
  );
  downloadHtmlFile(
    html,
    `${slugifyFilename(projectName)}-validation-report.html`,
  );
}

function escapeMarkdownInline(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\[/g, "\\[");
}

function markdownCitationLink(citation: Citation): string {
  const label = citation.title || citation.url || "Source";
  if (isSafeHttpUrl(citation.url)) {
    return `[${escapeMarkdownInline(label)}](${citation.url})`;
  }
  return escapeMarkdownInline(label);
}

function markdownParagraphs(text: string, maxChars = 380): string {
  const paragraphs = splitReadableParagraphs(text, maxChars);
  if (paragraphs.length === 0) return "";
  return paragraphs.map((paragraph) => `${paragraph}\n`).join("\n");
}

function markdownFinding(
  finding: Finding,
  findingIndex: number,
  citationIndexMap: Map<string, number>,
): string {
  const lines: string[] = [
    `#### Finding ${findingIndex} (${finding.confidence} confidence)`,
    "",
    finding.claim,
    "",
  ];

  const evidenceParagraphs = splitReadableParagraphs(finding.evidence_summary, 420);
  if (evidenceParagraphs.length > 0) {
    lines.push("**Evidence**", "");
    for (const paragraph of evidenceParagraphs) {
      lines.push(paragraph, "");
    }
  }

  if (finding.citations.length > 0) {
    const refs = finding.citations
      .map((citation) => {
        const key = citation.url || citation.title;
        const index = citationIndexMap.get(key);
        if (index) return `[${index}]`;
        return null;
      })
      .filter((ref): ref is string => ref !== null);
    if (refs.length > 0) {
      lines.push(`Sources: ${refs.join(", ")}`, "");
    }
  }

  if (finding.confidence_rationale) {
    lines.push(`*${finding.confidence_rationale}*`, "");
  }

  return lines.join("\n");
}

function markdownRiskSection(text: string): string {
  const parsed = parseRiskAssessment(text);
  if (!parsed.isStructured) {
    return markdownParagraphs(text);
  }

  const lines: string[] = [];
  if (parsed.preamble) {
    lines.push(markdownParagraphs(parsed.preamble), "");
  }

  for (const risk of parsed.items) {
    lines.push(`### Risk ${risk.number}: ${risk.title}`);
    if (risk.verdict) {
      lines.push(`**${risk.verdict}**`, "");
    }
    if (risk.body) {
      lines.push(markdownParagraphs(risk.body), "");
    }
  }

  return lines.join("\n");
}

function markdownScoresSection(report: ValidationReport): string {
  const { sections, overall } = resolveReportScores(report);
  const lines = [
    "## Scores",
    "",
    `**Overall score:** ${overall}/100`,
    "",
    "| Section | Score |",
    "| --- | ---: |",
    ...sections.map((section) => `| ${section.label} | ${section.score} |`),
    "",
  ];
  return lines.join("\n");
}

export function buildValidationReportMarkdown(
  report: ValidationReport,
  projectName: string,
): string {
  const citations = collectAllCitations(report);
  const citationIndexMap = buildCitationIndexMap(citations);
  const showRecommendation =
    report.overall_recommendation !== "too_vague_to_recommend";
  const questionCount = report.questions_and_findings.length;
  const findingCount = countFindings(report);
  const exportedAt = new Date().toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const lines: string[] = [
    `# ${projectName} — Validation Report`,
    "",
    `*Exported ${exportedAt} · Generated by Fivvle research engine · Rubric ${report.rubric_version_used}*`,
    "",
  ];

  if (showRecommendation) {
    lines.push(
      `**Recommendation:** ${formatRecommendation(report.overall_recommendation)}`,
      "",
    );
  }

  lines.push(
    `- **${questionCount}** research questions`,
    `- **${findingCount}** findings`,
    `- **${citations.length}** sources`,
    "",
  );

  lines.push(markdownScoresSection(report));

  if (showRecommendation && report.recommendation_rationale) {
    lines.push("## Recommendation", "", markdownParagraphs(report.recommendation_rationale), "");
  }

  lines.push("## Executive summary", "", markdownParagraphs(report.executive_summary), "");

  lines.push("## Research findings", "");

  for (const [qIndex, qf] of report.questions_and_findings.entries()) {
    const displayIndex = questionDisplayIndex(qf.question_id, qIndex + 1);
    const qScore = resolveQuestionScore(qf);
    lines.push(
      `### ${displayIndex}: ${qf.question}`,
      "",
      `*Score: ${qScore}/100 · ${qf.findings.length} finding${qf.findings.length === 1 ? "" : "s"}*`,
      "",
    );

    for (const [fIndex, finding] of qf.findings.entries()) {
      lines.push(markdownFinding(finding, fIndex + 1, citationIndexMap));
    }

    if (qf.evidence_gap) {
      lines.push(`> **Evidence gap:** ${qf.evidence_gap}`, "");
    }
  }

  if (report.competitors.length > 0) {
    lines.push("## Competitors", "");
    for (const comp of report.competitors) {
      lines.push(`### ${comp.name}`, "", markdownParagraphs(comp.description, 320));
      if (comp.positioning_vs_idea) {
        lines.push("", `**vs. your idea:** ${comp.positioning_vs_idea}`, "");
      }
      if (comp.citations.length > 0) {
        lines.push(
          "Sources:",
          ...comp.citations.map((citation) => `- ${markdownCitationLink(citation)}`),
          "",
        );
      }
    }
  }

  const marketBlocks: string[] = [];
  if (report.market_signals) {
    marketBlocks.push("### Market overview", "", markdownParagraphs(report.market_signals), "");
  }
  if (report.distribution_signals) {
    marketBlocks.push("### Distribution", "", markdownParagraphs(report.distribution_signals), "");
  }
  if (report.regulatory_signals) {
    marketBlocks.push("### Regulatory", "", markdownParagraphs(report.regulatory_signals), "");
  }
  if (marketBlocks.length > 0) {
    lines.push("## Market signals", "", ...marketBlocks);
  }

  if (report.risks_assessment) {
    lines.push("## Risk assessment", "", markdownRiskSection(report.risks_assessment), "");
  }

  if (report.research_limitations) {
    lines.push(
      "## Research limitations",
      "",
      markdownParagraphs(report.research_limitations),
      "",
    );
  }

  if (citations.length > 0) {
    lines.push(`## Sources (${citations.length})`, "");
    for (const [index, citation] of citations.entries()) {
      const link = markdownCitationLink(citation);
      const domain = citation.source_domain ? ` — ${citation.source_domain}` : "";
      lines.push(`${index + 1}. ${link}${domain}`);
    }
    lines.push("");
  }

  return lines.join("\n").trimEnd() + "\n";
}

function downloadMarkdownFile(markdown: string, filename: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadValidationReportMarkdown(
  report: ValidationReport,
  projectName = "validation-report",
): void {
  const markdown = buildValidationReportMarkdown(report, projectName);
  downloadMarkdownFile(
    markdown,
    `${slugifyFilename(projectName)}-validation-report.md`,
  );
}
```

### `lib/validation-report-scores.ts`

```typescript
import type {
  QuestionFindings,
  SectionScore,
  ValidationReport,
} from "@/lib/types";

export type ReportSectionId =
  | "market"
  | "competition"
  | "distribution"
  | "regulatory"
  | "risk"
  | "research";

export interface ResolvedReportScores {
  sections: SectionScore[];
  overall: number;
  derived: boolean;
}

const CONFIDENCE_POINTS: Record<QuestionFindings["findings"][number]["confidence"], number> = {
  high: 88,
  medium: 68,
  low: 48,
};

const SECTION_LABELS: Record<ReportSectionId, string> = {
  market: "Market demand",
  competition: "Competition",
  distribution: "Distribution",
  regulatory: "Regulatory",
  risk: "Risk profile",
  research: "Research depth",
};

const SECTION_WEIGHTS: Record<ReportSectionId, number> = {
  market: 0.25,
  competition: 0.15,
  distribution: 0.1,
  regulatory: 0.05,
  risk: 0.2,
  research: 0.25,
};

function clampScore(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

export function scoreTone(score: number): "strong" | "mixed" | "weak" {
  if (score >= 70) return "strong";
  if (score >= 45) return "mixed";
  return "weak";
}

function questionScore(qf: QuestionFindings): number {
  if (qf.score != null) return clampScore(qf.score);
  if (qf.findings.length === 0) return 35;
  const avg =
    qf.findings.reduce((sum, f) => sum + CONFIDENCE_POINTS[f.confidence], 0) /
    qf.findings.length;
  const gapPenalty = qf.evidence_gap ? 12 : 0;
  return clampScore(avg - gapPenalty);
}

function recommendationRiskScore(report: ValidationReport): number {
  switch (report.overall_recommendation) {
    case "proceed":
      return 78;
    case "iterate":
      return 62;
    case "pivot":
      return 46;
    case "kill":
      return 28;
    case "too_vague_to_recommend":
      return 38;
  }
}

function deriveSectionScores(report: ValidationReport): SectionScore[] {
  const questionScores = report.questions_and_findings.map(questionScore);
  const researchAvg =
    questionScores.length > 0
      ? questionScores.reduce((a, b) => a + b, 0) / questionScores.length
      : 40;

  const competitionScore = clampScore(
    report.competitors.length === 0
      ? 42
      : 48 + report.competitors.length * 7 + Math.min(researchAvg * 0.15, 12),
  );

  const distributionScore = clampScore(
    report.distribution_signals?.trim() ? 68 : 38,
  );

  const regulatoryScore = clampScore(
    report.regulatory_signals?.trim() ? 65 : 45,
  );

  const marketScore = clampScore(researchAvg * 0.55 + (report.market_signals?.trim() ? 22 : 8));

  const ids: ReportSectionId[] = [
    "market",
    "competition",
    "distribution",
    "regulatory",
    "risk",
    "research",
  ];

  const values: Record<ReportSectionId, number> = {
    market: marketScore,
    competition: competitionScore,
    distribution: distributionScore,
    regulatory: regulatoryScore,
    risk: recommendationRiskScore(report),
    research: clampScore(researchAvg),
  };

  return ids.map((section_id) => ({
    section_id,
    label: SECTION_LABELS[section_id],
    score: values[section_id],
  }));
}

function weightedOverall(sections: SectionScore[]): number {
  let total = 0;
  let weight = 0;
  for (const section of sections) {
    const w = SECTION_WEIGHTS[section.section_id as ReportSectionId] ?? 0;
    total += section.score * w;
    weight += w;
  }
  return clampScore(weight > 0 ? total / weight : 0);
}

export function resolveReportScores(report: ValidationReport): ResolvedReportScores {
  const storedSections = report.section_scores ?? [];
  const hasStored = storedSections.length >= 6 && report.overall_score != null;

  if (hasStored) {
    return {
      sections: storedSections.slice(0, 6),
      overall: clampScore(report.overall_score!),
      derived: false,
    };
  }

  const sections = deriveSectionScores(report);
  return {
    sections,
    overall: weightedOverall(sections),
    derived: true,
  };
}

export function resolveQuestionScore(qf: QuestionFindings): number {
  return questionScore(qf);
}
```

### `lib/validation-report-score-details.ts`

```typescript
import type { SectionScore, ValidationReport } from "@/lib/types";
import type { ReportSectionId } from "@/lib/validation-report-scores";
import { resolveQuestionScore } from "@/lib/validation-report-scores";

export type ScoreSelectionId = ReportSectionId | "overall";

export interface SectionScoreDetail extends SectionScore {
  rationale: string;
  pros: string[];
  cons: string[];
  context: string;
}

export interface OverallScoreDetail {
  id: "overall";
  label: string;
  score: number;
  rationale: string;
  pros: string[];
  cons: string[];
  context: string;
}

function truncate(text: string, max = 360): string {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trim()}…`;
}

function highConfidenceCount(report: ValidationReport): number {
  return report.questions_and_findings.reduce(
    (total, qf) =>
      total + qf.findings.filter((f) => f.confidence === "high").length,
    0,
  );
}

function gapCount(report: ValidationReport): number {
  return report.questions_and_findings.filter((qf) => qf.evidence_gap?.trim()).length;
}

function storedDetail(section: SectionScore): Partial<SectionScoreDetail> | null {
  const hasRationale = Boolean(section.rationale?.trim());
  const hasPros = (section.pros?.length ?? 0) > 0;
  const hasCons = (section.cons?.length ?? 0) > 0;
  if (!hasRationale && !hasPros && !hasCons) return null;
  return {
    rationale: section.rationale?.trim() ?? "",
    pros: section.pros ?? [],
    cons: section.cons ?? [],
  };
}

function buildMarketDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const high = highConfidenceCount(report);
  const gaps = gapCount(report);
  const context = report.market_signals?.trim()
    ? truncate(report.market_signals)
    : "No dedicated market signals section in this report.";

  return {
    section_id: "market",
    label: "Market demand",
    score,
    context,
    rationale:
      score >= 70
        ? "Demand signals are supported by multiple cited findings and substantive market evidence."
        : score >= 45
          ? "Some demand indicators exist, but market evidence is mixed or partially gaps-filled."
          : "Market demand evidence is thin — few corroborated signals or explicit gaps noted.",
    pros: [
      ...(report.market_signals?.trim()
        ? ["Market signals section cites observable demand or category activity."]
        : []),
      ...(high >= 2 ? [`${high} high-confidence findings support demand-related claims.`] : []),
    ],
    cons: [
      ...(gaps > 0 ? [`${gaps} research question(s) flagged evidence gaps.`] : []),
      ...(!report.market_signals?.trim()
        ? ["No structured market signals narrative was produced."]
        : []),
      ...(report.research_limitations.toLowerCase().includes("market")
        ? ["Research limitations note missing or weak market-size data."]
        : []),
    ],
  };
}

function buildCompetitionDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const names = report.competitors.map((c) => c.name).slice(0, 4);
  const context =
    report.competitors.length > 0
      ? report.competitors
          .map((c) => `${c.name}: ${truncate(c.positioning_vs_idea, 140)}`)
          .join("\n\n")
      : "No named competitors were surfaced in the research.";

  return {
    section_id: "competition",
    label: "Competition",
    score,
    context: truncate(context, 420),
    rationale:
      report.competitors.length === 0
        ? "Competitive landscape is unclear — no named, cited competitors in the report."
        : score >= 70
          ? "Competitive landscape is well mapped with named players and cited positioning."
          : "Competitors are identified but overlap or differentiation remains uncertain.",
    pros: [
      ...(names.length > 0
        ? [`${report.competitors.length} named competitor(s): ${names.join(", ")}.`]
        : []),
      ...(report.competitors.some((c) => c.citations.length > 0)
        ? ["Competitor claims include source citations."]
        : []),
    ],
    cons: [
      ...(report.competitors.length >= 4
        ? ["Crowded competitive set — differentiation must be sharp."]
        : []),
      ...(report.competitors.length === 0
        ? ["No verified competitors — may indicate weak search coverage or vague category."]
        : []),
    ],
  };
}

function buildDistributionDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = report.distribution_signals?.trim()
    ? truncate(report.distribution_signals)
    : "Distribution was not substantively covered — no distribution signals section.";

  return {
    section_id: "distribution",
    label: "Distribution",
    score,
    context,
    rationale: report.distribution_signals?.trim()
      ? "Acquisition or channel evidence appears in the report."
      : "Little to no cited evidence on how this idea would reach customers.",
    pros: report.distribution_signals?.trim()
      ? ["Distribution signals reference concrete channels or growth mechanics."]
      : [],
    cons: report.distribution_signals?.trim()
      ? []
      : ["No distribution_signals narrative — go-to-market path is unvalidated."],
  };
}

function buildRegulatoryDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = report.regulatory_signals?.trim()
    ? truncate(report.regulatory_signals)
    : "No regulatory or compliance angle was investigated for this idea.";

  return {
    section_id: "regulatory",
    label: "Regulatory",
    score,
    context,
    rationale: report.regulatory_signals?.trim()
      ? "Regulatory or compliance factors were researched and documented."
      : "Regulatory dimension appears low-relevance or was not evidenced in research.",
    pros: report.regulatory_signals?.trim()
      ? ["Regulatory constraints or requirements are explicitly documented."]
      : ["No apparent regulatory blocker surfaced in available evidence."],
    cons: report.regulatory_signals?.trim()
      ? ["Compliance requirements may add launch friction or cost."]
      : ["Regulatory exposure was not deeply investigated — unknown risk remains."],
  };
}

function buildRiskDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const context = truncate(report.risks_assessment);

  return {
    section_id: "risk",
    label: "Risk profile",
    score,
    context,
    rationale:
      report.overall_recommendation === "kill"
        ? "Material risks appear fatal or poorly mitigated based on the assessment."
        : report.overall_recommendation === "proceed"
          ? "Key risks were investigated and appear manageable relative to opportunity."
          : "Risks are documented but several remain partially confirmed or unaddressed.",
    pros: [
      ...(report.risks_assessment.length > 80
        ? ["Risk assessment engages specific risks from refinement."]
        : []),
      ...(report.overall_recommendation === "proceed"
        ? ["Recommendation suggests risk profile is acceptable to move forward."]
        : []),
    ],
    cons: [
      ...(report.overall_recommendation === "kill" || report.overall_recommendation === "pivot"
        ? [`Overall recommendation is ${report.overall_recommendation} — elevated downside.`]
        : []),
      ...(gapCount(report) > 0 ? ["Some research questions left evidence gaps on related risks."] : []),
    ],
  };
}

function buildResearchDetail(report: ValidationReport, score: number): SectionScoreDetail {
  const gaps = report.questions_and_findings.filter((qf) => qf.evidence_gap?.trim());
  const low = report.questions_and_findings.filter((qf) =>
    qf.findings.every((f) => f.confidence === "low"),
  );
  const context = report.questions_and_findings
    .map((qf) => {
      const qScore = resolveQuestionScore(qf);
      const gap = qf.evidence_gap ? ` Gap: ${truncate(qf.evidence_gap, 100)}` : "";
      return `${qf.question_id.toUpperCase()} (${qScore}/100): ${truncate(qf.question, 120)}${gap}`;
    })
    .join("\n");

  return {
    section_id: "research",
    label: "Research depth",
    score,
    context: truncate(context, 420),
    rationale:
      score >= 70
        ? "Most research questions are answered with corroborated, medium-to-high confidence findings."
        : score >= 45
          ? "Research coverage is partial — some questions lack depth or cite thin evidence."
          : "Research depth is weak — multiple low-confidence findings or unanswered gaps.",
    pros: [
      `${report.questions_and_findings.length} research questions investigated.`,
      ...(highConfidenceCount(report) >= 3
        ? [`${highConfidenceCount(report)} high-confidence findings across the report.`]
        : []),
    ],
    cons: [
      ...(gaps.length > 0
        ? [`Evidence gaps on: ${gaps.map((g) => g.question_id).join(", ")}.`]
        : []),
      ...(low.length > 0
        ? [`Low-confidence only on: ${low.map((g) => g.question_id).join(", ")}.`]
        : []),
    ],
  };
}

function mergeStored(
  derived: SectionScoreDetail,
  stored: Partial<SectionScoreDetail> | null,
): SectionScoreDetail {
  if (!stored) return derived;
  return {
    ...derived,
    rationale: stored.rationale || derived.rationale,
    pros: stored.pros?.length ? stored.pros : derived.pros,
    cons: stored.cons?.length ? stored.cons : derived.cons,
  };
}

function buildDerivedDetail(
  report: ValidationReport,
  section: SectionScore,
): SectionScoreDetail {
  switch (section.section_id) {
    case "market":
      return buildMarketDetail(report, section.score);
    case "competition":
      return buildCompetitionDetail(report, section.score);
    case "distribution":
      return buildDistributionDetail(report, section.score);
    case "regulatory":
      return buildRegulatoryDetail(report, section.score);
    case "risk":
      return buildRiskDetail(report, section.score);
    case "research":
      return buildResearchDetail(report, section.score);
  }
}

export function buildSectionScoreDetails(
  report: ValidationReport,
  sections: SectionScore[],
): SectionScoreDetail[] {
  return sections.map((section) =>
    mergeStored(buildDerivedDetail(report, section), storedDetail(section)),
  );
}

export function buildOverallScoreDetail(
  report: ValidationReport,
  overall: number,
): OverallScoreDetail {
  const rec = report.overall_recommendation;
  const context = truncate(
    [report.recommendation_rationale, report.executive_summary]
      .filter(Boolean)
      .join("\n\n"),
    420,
  );

  const recLabel =
    rec === "too_vague_to_recommend"
      ? "needs clarity"
      : rec.replace("_", " ");

  return {
    id: "overall",
    label: "Overall score",
    score: overall,
    context,
    rationale: `Composite validation score reflecting market, competition, distribution, regulatory, risk, and research depth. Recommendation: ${recLabel}.`,
    pros: [
      ...(rec === "proceed" ? ["Research supports moving forward with the current thesis."] : []),
      ...(overall >= 70 ? ["Multiple dimensions score above 70."] : []),
      ...(highConfidenceCount(report) >= 4
        ? ["Strong volume of high-confidence findings."]
        : []),
    ],
    cons: [
      ...(rec === "kill" || rec === "pivot"
        ? [`Verdict is ${recLabel} — composite score reflects serious concerns.`]
        : []),
      ...(gapCount(report) > 0
        ? [`${gapCount(report)} research area(s) have documented evidence gaps.`]
        : []),
      ...(report.research_limitations.trim()
        ? ["See research limitations for uncovered dimensions."]
        : []),
    ],
  };
}

export function findScoreDetail(
  details: SectionScoreDetail[],
  id: ScoreSelectionId,
): SectionScoreDetail | OverallScoreDetail | null {
  if (id === "overall") return null;
  return details.find((d) => d.section_id === id) ?? null;
}
```

## 5. Shared components

### `components/ui/EmptyState.tsx`

```typescript
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`fv-fade-up flex flex-col items-center px-6 py-16 text-center ${className}`}
    >
      {icon && (
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--fv-accent-muted)] ring-1 ring-[color-mix(in_srgb,var(--fv-accent)_20%,transparent)]">
          {icon}
        </div>
      )}
      <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--fv-text)]">
        {title}
      </h2>
      {description && (
        <p className="mt-2 max-w-md text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
```

### `components/ui/ErrorBanner.tsx`

```typescript
import { AlertCircle, X } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorBanner({
  message,
  onDismiss,
  className = "",
}: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={`fv-error flex items-start gap-3 ${className}`}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--fv-danger-light)]" />
      <p className="min-w-0 flex-1 text-sm leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="fv-icon-btn shrink-0 !h-7 !w-7"
          aria-label="Dismiss error"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
```

### `components/ui/LoadingState.tsx`

```typescript
import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export function LoadingState({
  label = "Loading…",
  className = "",
}: LoadingStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-16 ${className}`}
    >
      <Loader2 className="h-6 w-6 animate-spin text-[var(--fv-accent)]" />
      <p className="text-sm text-[var(--fv-text-muted)]">{label}</p>
    </div>
  );
}
```

### `components/ui/PageHeader.tsx`

```typescript
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: ReactNode;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  /** Tighter spacing for full-height workspace views (e.g. experiment detail). */
  compact?: boolean;
}

export function PageHeader({
  title,
  description,
  badge,
  actions,
  compact = false,
}: PageHeaderProps) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-3 ${
        compact ? "mb-2" : "mb-6 gap-4"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {typeof title === "string" ? (
            <h1
              className={`font-semibold tracking-[-0.02em] text-[var(--fv-text)] ${
                compact ? "text-lg sm:text-xl" : "text-xl sm:text-2xl"
              }`}
            >
              {title}
            </h1>
          ) : (
            title
          )}
          {badge}
        </div>
        {description && !compact && (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--fv-text-muted)]">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}
```

### `components/ui/ToastProvider.tsx`

```typescript
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

type ToastVariant = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (message: string, variant?: ToastVariant) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const MAX_TOASTS = 3;
const AUTO_DISMISS_MS = 3000;

const variantStyles: Record<
  ToastVariant,
  { bg: string; text: string; border: string }
> = {
  success: {
    bg: "rgba(16, 185, 129, 0.15)",
    text: "var(--fv-success)",
    border: "rgba(16, 185, 129, 0.3)",
  },
  error: {
    bg: "rgba(239, 68, 68, 0.15)",
    text: "var(--fv-danger)",
    border: "rgba(239, 68, 68, 0.3)",
  },
  info: {
    bg: "var(--fv-accent-muted)",
    text: "var(--fv-accent)",
    border: "color-mix(in srgb, var(--fv-accent) 30%, transparent)",
  },
};

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const [visible, setVisible] = useState(false);
  const styles = variantStyles[toast.variant];

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(timer);
    };
  }, [onDismiss]);

  return (
    <div
      className="pointer-events-auto rounded-full px-4 py-2 text-sm font-medium shadow-lg transition-all duration-300 ease-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(8px)",
        background: styles.bg,
        color: styles.text,
        border: `1px solid ${styles.border}`,
      }}
    >
      {toast.message}
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextIdRef = useRef(0);

  const toast = useCallback(
    (message: string, variant: ToastVariant = "info") => {
      const id = nextIdRef.current++;
      setToasts((prev) => {
        const next = [...prev, { id, message, variant }];
        return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next;
      });
    },
    [],
  );

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            toast={t}
            onDismiss={() => dismissToast(t.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
```

### `components/ui/TypeConfirmDialog.tsx`

```typescript
"use client";

import { useEffect, useId, useState, type ReactNode } from "react";
import { Loader2, X } from "lucide-react";
import { ErrorBanner } from "@/components/ui/ErrorBanner";

export interface TypeConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description: ReactNode;
  /** Word the user must type exactly (default: CONFIRM). */
  confirmWord?: string;
  /** Primary action label when ready. */
  confirmLabel?: string;
  /** Icon shown in the dialog header. */
  icon?: ReactNode;
  loading?: boolean;
  error?: string | null;
  onConfirm: () => void | Promise<void>;
}

export function TypeConfirmDialog({
  open,
  onClose,
  title,
  description,
  confirmWord = "CONFIRM",
  confirmLabel = "Confirm",
  icon,
  loading = false,
  error = null,
  onConfirm,
}: TypeConfirmDialogProps) {
  const inputId = useId();
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (!open) {
      setTyped("");
    }
  }, [open]);

  if (!open) return null;

  const canConfirm = typed === confirmWord && !loading;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${inputId}-title`}
    >
      <div className="w-full max-w-md rounded-2xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {icon ? (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--fv-danger)]/10 text-[var(--fv-danger)]">
                {icon}
              </div>
            ) : null}
            <div>
              <h2
                id={`${inputId}-title`}
                className="text-lg font-semibold text-[var(--fv-text)]"
              >
                {title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="fv-icon-btn shrink-0"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="text-sm leading-relaxed text-[var(--fv-text-muted)]">
          {description}
        </div>

        <div className="mt-4">
          <label
            htmlFor={inputId}
            className="mb-1.5 block text-[12px] font-medium text-[var(--fv-text-soft)]"
          >
            Type <span className="font-mono text-[var(--fv-text)]">{confirmWord}</span>{" "}
            to continue
          </label>
          <input
            id={inputId}
            type="text"
            value={typed}
            disabled={loading}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            className="fv-input w-full rounded-lg border border-[var(--fv-border)] bg-white/[0.03] px-3 py-2.5 font-mono text-[13px]"
            placeholder={confirmWord}
          />
        </div>

        {error && <ErrorBanner message={error} className="mt-4" />}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void onConfirm()}
            disabled={!canConfirm}
            className="fv-btn-primary bg-[var(--fv-danger)] px-4 py-2 text-sm hover:bg-red-500 disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Working…
              </span>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
```

## 6. Routing and state

### `app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { DM_Mono, Inter } from "next/font/google";
import { AppProviders } from "@/components/providers/AppProviders";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-dm-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fivvle — Validate Your Startup Idea",
  description: "Validate your startup idea with real signal.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`h-full antialiased ${inter.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("fivvle-theme");var m=localStorage.getItem("fivvle-reduced-motion");if(m==="true")document.documentElement.setAttribute("data-reduced-motion","true");var r=t==="light"?"light":t==="dark"?"dark":t==="system"?(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):"dark";document.documentElement.setAttribute("data-theme",r);}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
```

### `app/(dashboard)/layout.tsx`

```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ToastProvider } from "@/components/ui/ToastProvider";

function DashboardGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex h-screen max-h-screen overflow-hidden bg-[var(--fv-bg)]">
        <aside className="sticky top-0 hidden h-screen w-[260px] shrink-0 self-start border-r border-[var(--fv-border)] bg-[var(--fv-surface)] p-4 lg:flex">
          <div className="fv-skeleton h-8 w-full rounded-xl" />
          <div className="fv-skeleton mt-5 h-10 w-full rounded-xl" />
          <div className="mt-8 space-y-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="fv-skeleton h-14 rounded-lg" />
            ))}
          </div>
        </aside>
        <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div
            className="flex h-16 shrink-0 items-center justify-between border-b px-4 sm:px-6"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
          >
            <div className="fv-skeleton h-8 w-24 rounded lg:hidden" />
            <div className="fv-skeleton h-8 w-8 rounded-full" />
          </div>
          <main className="flex-1 overflow-y-auto p-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="fv-skeleton h-40 rounded-xl" />
              ))}
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <DashboardGuard>
        <ToastProvider>
          <DashboardShell>{children}</DashboardShell>
        </ToastProvider>
      </DashboardGuard>
    </AuthProvider>
  );
}
```

### `app/(dashboard)/dashboard/layout.tsx`

```typescript
export default function DashboardPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
```

### `app/(dashboard)/experiment/[id]/page.tsx`

```typescript
"use client";

import { ExperimentDetailPanel } from "@/components/dashboard/ExperimentDetailPanel";
import type { ExperimentStageId } from "@/lib/experiment-stages";
import { useParams, useSearchParams } from "next/navigation";

function parseInitialStage(value: string | null): ExperimentStageId | undefined {
  if (
    value === "refine" ||
    value === "report" ||
    value === "landing" ||
    value === "metrics" ||
    value === "insight"
  ) {
    return value;
  }
  return undefined;
}

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const initialStage = parseInitialStage(searchParams.get("stage"));

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ExperimentDetailPanel
        experimentId={params.id}
        initialStage={initialStage}
      />
    </div>
  );
}
```

### `middleware.ts`

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  LANDING_SLUG_PATTERN,
  resolveProjectSlugFromHost,
} from "@/lib/landing-host";

/** App routes that must not be served on project subdomains. */
const APP_ROUTE_PREFIXES = [
  "/dashboard",
  "/experiment",
  "/login",
  "/signup",
  "/admin",
  "/archived",
  "/new",
  "/api",
  "/preview",
  "/refinement-demos",
] as const;

function isAppRoute(pathname: string): boolean {
  return APP_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function internalLandingPath(slug: string): string {
  return `/e/${slug}`;
}

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  const slug = resolveProjectSlugFromHost(host);

  if (!slug) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Already rewritten to the internal landing route — avoid loops.
  const internalPrefix = internalLandingPath(slug);
  if (pathname === internalPrefix || pathname.startsWith(`${internalPrefix}/`)) {
    const pathSlugMatch = pathname.match(/^\/e\/([a-z0-9-]{6,40})(?:\/|$)/);
    if (pathSlugMatch && pathSlugMatch[1] !== slug) {
      return new NextResponse(null, { status: 404 });
    }
    return NextResponse.next();
  }

  if (isAppRoute(pathname)) {
    return new NextResponse(null, { status: 404 });
  }

  // Only the landing page root is public on project subdomains.
  if (pathname !== "/" && pathname !== "") {
    return new NextResponse(null, { status: 404 });
  }

  const rewriteUrl = request.nextUrl.clone();
  rewriteUrl.pathname = internalPrefix;
  return NextResponse.rewrite(rewriteUrl);
}

export const config = {
  matcher: [
    /*
     * Run on all paths except Next static assets and common static files.
     */
    "/((?!_next/static|_next/image|favicon.ico|icon.png|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};

// Re-export for tests / tooling that import slug validation from middleware.
export { LANDING_SLUG_PATTERN };
```

### `lib/auth-context.tsx`

```typescript
"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider,
  signOut,
  type User,
} from "firebase/auth";
import { FirebaseError } from "firebase/app";
import { getFirebaseAuth } from "./firebase";
import { syncUser } from "./api";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  refreshProfile: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  logOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  async function syncAppUser(firebaseUser: User): Promise<void> {
    try {
      const profile = await syncUser(firebaseUser);
      setIsAdmin(profile.is_admin);
    } catch {
      setIsAdmin(false);
    }
  }

  async function refreshProfile(): Promise<void> {
    const auth = getFirebaseAuth();
    const firebaseUser = auth.currentUser;
    if (!firebaseUser) {
      setIsAdmin(false);
      return;
    }
    await syncAppUser(firebaseUser);
  }

  useEffect(() => {
    const auth = getFirebaseAuth();
    let cancelled = false;

    async function handleRedirectResult() {
      try {
        const credential = await getRedirectResult(auth);
        if (credential?.user && !cancelled) {
          await syncAppUser(credential.user);
        }
      } catch {
        /* surfaced via auth state / login UI if needed */
      }
    }

    void handleRedirectResult();

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        void syncAppUser(firebaseUser).finally(() => {
          if (!cancelled) setLoading(false);
        });
      } else {
        setIsAdmin(false);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  async function signUp(email: string, password: string): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await createUserWithEmailAndPassword(
      auth,
      email,
      password,
    );
    await syncAppUser(credential.user);
  }

  async function signIn(email: string, password: string): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await signInWithEmailAndPassword(auth, email, password);
    await syncAppUser(credential.user);
  }

  async function signInWithGoogle(): Promise<void> {
    const auth = getFirebaseAuth();
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });

    try {
      const credential = await signInWithPopup(auth, provider);
      await syncAppUser(credential.user);
    } catch (err) {
      const shouldRedirect =
        err instanceof FirebaseError &&
        (err.code === "auth/popup-blocked" ||
          err.code === "auth/internal-error" ||
          err.code === "auth/cancelled-popup-request");

      if (shouldRedirect) {
        await signInWithRedirect(auth, provider);
        return;
      }
      throw err;
    }
  }

  async function logOut(): Promise<void> {
    const auth = getFirebaseAuth();
    setIsAdmin(false);
    await signOut(auth);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAdmin,
        refreshProfile,
        signUp,
        signIn,
        signInWithGoogle,
        logOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Returns null when rendered outside AuthProvider (e.g. marketing pages). */
export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}
```

### `components/providers/AppProviders.tsx`

```typescript
"use client";

import type { ReactNode } from "react";
import { PreferencesProvider } from "@/lib/preferences-context";

export function AppProviders({ children }: { children: ReactNode }) {
  return <PreferencesProvider>{children}</PreferencesProvider>;
}
```

### `components/dashboard/ExperimentDetailPanel.tsx`

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArchiveRestore,
  Archive,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import {
  confirmExperiment,
  generateInsight,
  generateLandingPage,
  getExperiment,
  getLandingPage,
  unarchiveExperiment,
  ApiError,
} from "@/lib/api";
import { useWallet } from "@/lib/wallet-context";
import type { Experiment, FounderDecision, LandingPage } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { RefineStagePanel } from "@/components/refinement/RefineStagePanel";
import { InsightStagePanel } from "@/components/insight/InsightStagePanel";
import { MetricsStagePanel } from "@/components/insight/MetricsStagePanel";
import { LandingGenerationProgress } from "@/components/research/LandingGenerationProgress";
import {
  TemplatePicker,
  type TemplateId,
} from "@/components/research/TemplatePicker";
import { ReportCanvas } from "@/components/research/ReportCanvas";
import { EditorLayout } from "@/components/landing-page-editor/EditorLayout";
import { EditorLoadingSkeleton } from "@/components/landing-page-editor/EditorLoadingSkeleton";
import { ExperimentStageNav } from "@/components/experiment/ExperimentStageNav";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { EditableProjectName } from "@/components/experiment/EditableProjectName";
import { ArchiveProjectDialog } from "@/components/experiment/ArchiveProjectDialog";
import { DeleteProjectDialog } from "@/components/experiment/DeleteProjectDialog";
import { getExperimentDisplayName } from "@/lib/experiment-name";
import { notifyExperimentsChanged } from "@/lib/experiment-events";
import { readPaidActionError } from "@/lib/wallet-errors";
import { syncWalletAfterPaidAction } from "@/lib/wallet-sync";
import {
  INSIGHT_PAYWALL_CREDITS,
  VALIDATION_PAYWALL_CREDITS,
} from "@/lib/wallet-paywall";
import {
  defaultStageForStatus,
  isStageUnlocked,
  pollIntervalForStatus,
  shouldPollExperimentStatus,
  shouldShowExperimentStageNav,
  type ExperimentStageId,
} from "@/lib/experiment-stages";
import { canViewLandingPageEditor } from "@/lib/landing-flow";

const DISTRIBUTE_VISIBLE_STATUSES = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const LANDING_PAGE_LOAD_RETRIES = 8;
const LANDING_PAGE_LOAD_RETRY_MS = 1500;

function templateStorageKey(experimentId: string): string {
  return `fivvle_lp_template_${experimentId}`;
}

function readStoredTemplate(experimentId: string): TemplateId | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(templateStorageKey(experimentId));
    if (!raw) return null;
    return raw as TemplateId;
  } catch {
    return null;
  }
}

function storeTemplate(experimentId: string, templateId: TemplateId): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(templateStorageKey(experimentId), templateId);
  } catch {
    /* ignore */
  }
}

interface ExperimentDetailPanelProps {
  experimentId: string;
  rawIdea?: string;
  nameRefreshKey?: number;
  initialStage?: ExperimentStageId;
}

export function ExperimentDetailPanel({
  experimentId,
  nameRefreshKey = 0,
  initialStage,
}: ExperimentDetailPanelProps) {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [generatingLp, setGeneratingLp] = useState(false);
  const [retryingInsight, setRetryingInsight] = useState(false);
  const [unarchiving, setUnarchiving] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId | null>(null);
  const [activeStage, setActiveStage] = useState<ExperimentStageId>(
    initialStage ?? "refine",
  );
  const [landingSlug, setLandingSlug] = useState<string | null>(null);
  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [landingPageLoading, setLandingPageLoading] = useState(false);
  const [landingPageError, setLandingPageError] = useState<string | null>(null);
  const [refinementFinalized, setRefinementFinalized] = useState(false);
  const { refresh: refreshWallet, applyWalletPatch } = useWallet();

  const loadExperiment = useCallback(async () => {
    try {
      const data = await getExperiment(experimentId);
      setExperiment(data);
      setError(null);
      if (data.status === "REFINED" || data.validation_report != null) {
        setRefinementFinalized(true);
      }
      setActiveStage((prev) => {
        if (isStageUnlocked(prev, data.status)) return prev;
        return defaultStageForStatus(data.status);
      });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "Experiment not found."
          : "Could not load experiment.",
      );
    } finally {
      setLoading(false);
    }
  }, [experimentId]);

  const loadLandingPage = useCallback(
    async (options: { retryOn404?: boolean } = {}) => {
      const retryOn404 = options.retryOn404 ?? false;
      setLandingPageLoading(true);
      setLandingPageError(null);

      const maxAttempts = retryOn404 ? LANDING_PAGE_LOAD_RETRIES : 1;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        try {
          const lp = await getLandingPage(experimentId);
          setLandingPage(lp);
          if (lp.slug) setLandingSlug(lp.slug);
          setLandingPageLoading(false);
          return;
        } catch (err) {
          const is404 = err instanceof ApiError && err.status === 404;
          const canRetry = retryOn404 && is404 && attempt < maxAttempts - 1;
          if (canRetry) {
            await new Promise((resolve) => {
              setTimeout(resolve, LANDING_PAGE_LOAD_RETRY_MS);
            });
            continue;
          }
          setLandingPage(null);
          if (is404) {
            setLandingPageError(
              "Landing page not found. It may still be generating.",
            );
          } else {
            setLandingPageError("Could not load landing page.");
          }
          setLandingPageLoading(false);
          return;
        }
      }
    },
    [experimentId],
  );

  useEffect(() => {
    setLoading(true);
    void loadExperiment();
  }, [loadExperiment, nameRefreshKey]);

  useEffect(() => {
    if (!experiment || !shouldPollExperimentStatus(experiment.status)) {
      return;
    }
    const intervalMs = pollIntervalForStatus(experiment.status);
    const intervalId = setInterval(() => void loadExperiment(), intervalMs);
    return () => clearInterval(intervalId);
  }, [experiment?.status, loadExperiment]);

  useEffect(() => {
    if (!experiment || !DISTRIBUTE_VISIBLE_STATUSES.has(experiment.status)) {
      setLandingSlug(null);
      return;
    }
    let cancelled = false;
    async function loadSlug() {
      try {
        const lp = await getLandingPage(experimentId);
        if (!cancelled && lp.slug) setLandingSlug(lp.slug);
      } catch {
        if (!cancelled) setLandingSlug(null);
      }
    }
    void loadSlug();
    return () => {
      cancelled = true;
    };
  }, [experiment, experimentId]);

  useEffect(() => {
    if (activeStage !== "landing") return;
    if (!experiment || !canViewLandingPageEditor(experiment.status)) {
      setLandingPage(null);
      setLandingPageError(null);
      return;
    }
    void loadLandingPage({ retryOn404: true });
  }, [activeStage, experiment, loadLandingPage]);

  useEffect(() => {
    const stored = readStoredTemplate(experimentId);
    if (stored) {
      setSelectedTemplate(stored);
    }
  }, [experimentId]);

  const handleLandingGenerationComplete = useCallback(() => {
    void loadExperiment();
    void loadLandingPage({ retryOn404: true });
  }, [loadExperiment, loadLandingPage]);

  const handleLandingGenerationFailed = useCallback(() => {
    void loadExperiment();
  }, [loadExperiment]);

  async function handleRetryResearch() {
    setRetrying(true);
    setError(null);
    try {
      const result = await confirmExperiment(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      await loadExperiment();
      setActiveStage("refine");
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        await refreshWallet();
      }
      setError(
        readPaidActionError(err, {
          fallbackRequired: VALIDATION_PAYWALL_CREDITS,
          fallback: "Could not restart research. Please try again.",
        }),
      );
    } finally {
      setRetrying(false);
    }
  }

  async function handleGenerateLandingPage() {
    if (!selectedTemplate) return;
    storeTemplate(experimentId, selectedTemplate);
    setGeneratingLp(true);
    try {
      await generateLandingPage(experimentId, { template_id: selectedTemplate });
      await loadExperiment();
      setActiveStage("landing");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 0) {
          setError("Could not reach the server. Check that the API is running.");
          return;
        }
        const body = err.body;
        if (
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail: unknown }).detail === "string"
        ) {
          setError((body as { detail: string }).detail);
          return;
        }
      }
      setError("Could not start landing page generation. Please try again.");
    } finally {
      setGeneratingLp(false);
    }
  }

  async function handleRetryInsight() {
    if (retryingInsight) return;
    setRetryingInsight(true);
    setError(null);
    try {
      const result = await generateInsight(experimentId);
      await syncWalletAfterPaidAction(
        refreshWallet,
        applyWalletPatch,
        result.credits_balance,
      );
      await loadExperiment();
      setActiveStage("insight");
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        await refreshWallet();
        setError(
          "Could not start insight generation. Your credits have been refunded — please try again.",
        );
        return;
      }
      setError(
        readPaidActionError(err, {
          fallbackRequired: INSIGHT_PAYWALL_CREDITS,
          fallback: "Could not start insight generation. Please try again.",
        }),
      );
    } finally {
      setRetryingInsight(false);
    }
  }

  async function handleUnarchive() {
    setUnarchiving(true);
    try {
      await unarchiveExperiment(experimentId);
      notifyExperimentsChanged();
      await loadExperiment();
    } catch {
      setError("Could not restore experiment. Please try again.");
    } finally {
      setUnarchiving(false);
    }
  }

  function handleDecision(_decision: FounderDecision) {
    notifyExperimentsChanged();
    void loadExperiment();
  }

  if (loading) {
    return (
      <div className="flex h-full min-h-0 flex-col p-3 sm:p-4">
        <div className="fv-skeleton mb-3 h-9 w-64 rounded-lg" />
        <div className="fv-skeleton min-h-0 flex-1 rounded-xl" />
      </div>
    );
  }

  if (error && !experiment) {
    return (
      <div className="flex items-center justify-center p-6 py-20">
        <ErrorBanner message={error} className="max-w-md" />
      </div>
    );
  }

  if (!experiment) return null;

  const status = experiment.status;
  const hasValidationReport = experiment.validation_report != null;
  const showStageNav = shouldShowExperimentStageNav(
    status,
    hasValidationReport,
    refinementFinalized,
  );
  const experimentDisplayName = getExperimentDisplayName(experiment);
  const showDistribute =
    DISTRIBUTE_VISIBLE_STATUSES.has(status) && landingSlug !== null;

  const headerActions = (
    <>
      {status === "RESEARCH_FAILED" && (
        <button
          type="button"
          onClick={() => void handleRetryResearch()}
          disabled={retrying}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {retrying ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Retry research
        </button>
      )}
      {status === "INSIGHT_FAILED" && (
        <button
          type="button"
          onClick={() => void handleRetryInsight()}
          disabled={retryingInsight}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {retryingInsight ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Retry insight
        </button>
      )}
      {status === "ARCHIVED" && (
        <button
          type="button"
          onClick={() => void handleUnarchive()}
          disabled={unarchiving}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {unarchiving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ArchiveRestore className="h-4 w-4" />
          )}
          Restore
        </button>
      )}
      {status !== "ARCHIVED" && (
        <button
          type="button"
          onClick={() => setArchiveDialogOpen(true)}
          className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-[var(--fv-text-muted)] hover:text-[var(--fv-danger)]"
        >
          <Archive className="h-4 w-4" />
          Archive
        </button>
      )}
      <button
        type="button"
        onClick={() => setDeleteDialogOpen(true)}
        className="fv-btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-[var(--fv-text-muted)] hover:text-[var(--fv-danger)]"
      >
        <Trash2 className="h-4 w-4" />
        Delete
      </button>
    </>
  );

  function renderStageContent(exp: Experiment) {
    const expStatus = exp.status;
    const expDisplayName = getExperimentDisplayName(exp);

    switch (activeStage) {
      case "refine":
        return (
          <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
            <RefineStagePanel
              experimentId={experimentId}
              onExperimentChange={loadExperiment}
              onRefinementFinalized={setRefinementFinalized}
            />
          </div>
        );

      case "report":
        if (!exp.validation_report) {
          return (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <LoadingState label="Research in progress — your report will appear here when ready." />
            </div>
          );
        }
        return (
          <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--fv-border)]">
            <ReportCanvas
              experimentId={experimentId}
              embedded
              projectName={expDisplayName}
            />
          </div>
        );

      case "landing":
        if (expStatus === "LANDING_GENERATING") {
          return (
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="fv-section-card">
                <LandingGenerationProgress
                  experimentId={experimentId}
                  onComplete={handleLandingGenerationComplete}
                  onFailed={handleLandingGenerationFailed}
                />
              </div>
            </div>
          );
        }
        if (canViewLandingPageEditor(expStatus)) {
          if (landingPageLoading) {
            return (
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <EditorLoadingSkeleton embedded />
              </div>
            );
          }
          if (landingPageError || !landingPage) {
            return (
              <div className="min-h-0 flex-1 overflow-y-auto">
                <ErrorBanner
                  message={landingPageError ?? "Landing page unavailable."}
                  className="max-w-lg"
                />
              </div>
            );
          }
          return (
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <EditorLayout
                embedded
                experimentId={experimentId}
                name={exp.name}
                rawIdea={exp.raw_idea ?? ""}
                experimentStatus={expStatus}
                landingPage={landingPage}
                onPublished={() => {
                  void loadExperiment();
                  void loadLandingPage();
                }}
                onExperimentRenamed={(nextName) => {
                  setExperiment((prev) =>
                    prev ? { ...prev, name: nextName } : prev,
                  );
                }}
                onRegenerateAll={() => {
                  void loadLandingPage();
                }}
              />
            </div>
          );
        }
        return (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="fv-section-card">
            <h3 className="text-lg font-semibold text-[var(--fv-text)]">
              Choose a template
            </h3>
            <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
              Pick a design for your validation landing page. You can customize
              all copy after generation.
            </p>
            <div className="mt-6">
              <TemplatePicker
                selectedId={selectedTemplate}
                onSelect={setSelectedTemplate}
                onGenerate={handleGenerateLandingPage}
                generating={generatingLp}
              />
            </div>
            </div>
          </div>
        );

      case "metrics":
        return (
          <MetricsStagePanel
            experimentId={experimentId}
            experimentStatus={expStatus}
            experimentName={expDisplayName}
            landingSlug={landingSlug}
            showDistribute={showDistribute}
            onInsightStarted={() => {
              setActiveStage("insight");
              void loadExperiment();
            }}
          />
        );

      case "insight":
        return (
          <InsightStagePanel
            experimentId={experimentId}
            experimentStatus={expStatus}
            onDecision={handleDecision}
          />
        );

      default:
        return null;
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col p-3 sm:p-4">
      <PageHeader
        compact
        title={
          <EditableProjectName
            experimentId={experimentId}
            name={experiment.name}
            rawIdea={experiment.raw_idea ?? ""}
            onRenamed={(nextName) => {
              setExperiment((prev) =>
                prev ? { ...prev, name: nextName } : prev,
              );
            }}
          />
        }
        badge={<StatusBadge status={status} />}
        actions={headerActions}
      />

      {error && (
        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
          className="mb-4"
        />
      )}

      {showStageNav && (
        <ExperimentStageNav
          activeStage={activeStage}
          status={status}
          onStageChange={setActiveStage}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {renderStageContent(experiment)}
      </div>

      <ArchiveProjectDialog
        experimentId={experimentId}
        projectName={experimentDisplayName}
        open={archiveDialogOpen}
        onClose={() => setArchiveDialogOpen(false)}
      />
      <DeleteProjectDialog
        experimentId={experimentId}
        projectName={experimentDisplayName}
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      />
    </div>
  );
}
```

### `components/experiment/ExperimentStageNav.tsx`

```typescript
"use client";

import {
  BarChart3,
  FileText,
  Layout,
  Lightbulb,
  Sparkles,
} from "lucide-react";
import type { ExperimentStageId } from "@/lib/experiment-stages";
import {
  EXPERIMENT_STAGES,
  isStageUnlocked,
} from "@/lib/experiment-stages";

const STAGE_ICONS: Record<ExperimentStageId, typeof Lightbulb> = {
  refine: Lightbulb,
  report: FileText,
  landing: Layout,
  metrics: BarChart3,
  insight: Sparkles,
};

interface ExperimentStageNavProps {
  activeStage: ExperimentStageId;
  status: string;
  onStageChange: (stage: ExperimentStageId) => void;
}

export function ExperimentStageNav({
  activeStage,
  status,
  onStageChange,
}: ExperimentStageNavProps) {
  return (
    <nav
      className="mb-2 shrink-0 overflow-x-auto sm:mb-3"
      aria-label="Project stages"
    >
      <div className="fv-experiment-stage-nav flex min-w-max gap-1 rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface)] p-1">
        {EXPERIMENT_STAGES.map((stage) => {
          const unlocked = isStageUnlocked(stage.id, status);
          const active = activeStage === stage.id;
          const Icon = STAGE_ICONS[stage.id];

          return (
            <button
              key={stage.id}
              type="button"
              disabled={!unlocked}
              onClick={() => unlocked && onStageChange(stage.id)}
              title={unlocked ? stage.description : "Not available yet"}
              className={`fv-stage-tab ${active ? "fv-stage-tab-active" : ""} ${
                !unlocked ? "fv-stage-tab-locked" : ""
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">{stage.shortLabel}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
```

### `lib/experiment-stages.ts`

```typescript
/** Maps experiment status to the founder journey stage for UI navigation. */

export type ExperimentStageId =
  | "refine"
  | "report"
  | "landing"
  | "metrics"
  | "insight";

export interface ExperimentStage {
  id: ExperimentStageId;
  label: string;
  shortLabel: string;
  description: string;
}

export const EXPERIMENT_STAGES: ExperimentStage[] = [
  {
    id: "refine",
    label: "Refine idea",
    shortLabel: "Refine",
    description: "Shape your idea through conversation before research runs.",
  },
  {
    id: "report",
    label: "Validation report",
    shortLabel: "Report",
    description: "Evidence-backed market research and recommendation.",
  },
  {
    id: "landing",
    label: "Landing page",
    shortLabel: "Landing",
    description: "Generate and customize your validation landing page.",
  },
  {
    id: "metrics",
    label: "Live metrics",
    shortLabel: "Metrics",
    description: "Page views, signups, and conversion by source.",
  },
  {
    id: "insight",
    label: "Insight & decision",
    shortLabel: "Insight",
    description: "Combined cognitive + behavioral signal and next steps.",
  },
];

const REPORT_UNLOCKED = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const LANDING_UNLOCKED = new Set([
  "RESEARCH_READY",
  "LANDING_GENERATING",
  "LANDING_DRAFT",
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const METRICS_UNLOCKED = new Set([
  "LANDING_LIVE",
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

const INSIGHT_UNLOCKED = new Set([
  "INSIGHT_GENERATING",
  "INSIGHT_READY",
  "INSIGHT_FAILED",
  "COMPLETED",
  "ARCHIVED",
]);

/** Experiment statuses while the research engine pipeline is running. */
export const RESEARCH_ACTIVE_STATUSES = new Set([
  "RESEARCHING",
  "RESEARCH_PLANNING",
  "RESEARCH_SEARCHING",
  "RESEARCH_READING",
  "RESEARCH_REFLECTING",
  "RESEARCH_SYNTHESIZING",
]);

/** Poll experiment detail while background jobs are in flight. */
export function shouldPollExperimentStatus(status: string): boolean {
  return (
    RESEARCH_ACTIVE_STATUSES.has(status) ||
    status === "LANDING_GENERATING" ||
    status === "INSIGHT_GENERATING"
  );
}

export function pollIntervalForStatus(status: string): number {
  if (status === "LANDING_GENERATING") return 5000;
  return 3000;
}

/** Show stage tabs once refinement is complete (Chapter 3) or a report exists. */
export function shouldShowExperimentStageNav(
  status: string,
  hasValidationReport: boolean,
  refinementFinalized = false,
): boolean {
  if (hasValidationReport || refinementFinalized) return true;
  if (status === "REFINED") return true;
  if (RESEARCH_ACTIVE_STATUSES.has(status) || status === "RESEARCH_FAILED") {
    return true;
  }
  return isStageUnlocked("report", status);
}

export function isStageUnlocked(
  stage: ExperimentStageId,
  status: string,
): boolean {
  switch (stage) {
    case "refine":
      return true;
    case "report":
      return REPORT_UNLOCKED.has(status);
    case "landing":
      return LANDING_UNLOCKED.has(status);
    case "metrics":
      return METRICS_UNLOCKED.has(status);
    case "insight":
      return INSIGHT_UNLOCKED.has(status);
    default:
      return false;
  }
}

export function defaultStageForStatus(status: string): ExperimentStageId {
  if (INSIGHT_UNLOCKED.has(status)) return "insight";
  if (METRICS_UNLOCKED.has(status)) return "metrics";
  if (status === "LANDING_DRAFT" || status === "LANDING_LIVE") return "landing";
  if (REPORT_UNLOCKED.has(status)) return "report";
  if (status.startsWith("RESEARCH") && status !== "RESEARCH_READY") return "refine";
  return "refine";
}

export function stageProgressIndex(stage: ExperimentStageId): number {
  return EXPERIMENT_STAGES.findIndex((s) => s.id === stage);
}
```

### `lib/experiment-events.ts`

```typescript
export const EXPERIMENTS_CHANGED_EVENT = "fivvle:experiments-changed";

export function notifyExperimentsChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(EXPERIMENTS_CHANGED_EVENT));
}
```

### Grep: useExperiment | ExperimentContext

```text
(no matches)
```

## 7. Backend API surface (frontend view)

### `lib/api.ts`

```typescript
import type { User as FirebaseUser } from "firebase/auth";
import { getFirebaseAuth } from "./firebase";
import { handleSessionExpired } from "./session-expired";
import type {
  ArchiveExperimentResponse,
  ChatTurnResponse,
  DeleteExperimentResponse,
  Experiment,
  ExperimentAnalytics,
  ExperimentChatMessagesResponse,
  ChatEditTurnResponse,
  ExperimentDetail,
  ExperimentSummary,
  FounderDecision,
  GenerateInsightResponse,
  GenerateLandingPageResponse,
  InsightReport,
  LandingPage,
  LandingPagePatch,
  LandingPageSlugAvailability,
  ResearchStatus,
  ValidationReport,
  WaitlistSignupsResponse,
} from "./types";
import type {
  GenerateLandingPageV2Request,
  GenerateLandingPageV2Response,
  LandingPageV2GenerationStatus,
} from "./landing-page-v2-types";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export class ApiError extends Error {
  public retryAfterSeconds: number | null;

  constructor(
    public status: number,
    public body: unknown,
    public requestId: string | null,
    retryAfterSeconds: number | null = null,
  ) {
    super(`API ${status}`);
    this.name = "ApiError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

type FetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  authenticated?: boolean;
  /** When set, skips auth.currentUser and uses this token directly. */
  idToken?: string;
  signal?: AbortSignal;
};

export async function apiFetch<T>(
  path: string,
  opts: FetchOptions = {},
): Promise<T> {
  const { method = "GET", body, authenticated = true, idToken, signal } = opts;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (authenticated) {
    let token = idToken;
    if (!token) {
      const auth = getFirebaseAuth();
      const user = auth.currentUser;
      if (!user) {
        await handleSessionExpired();
        throw new ApiError(401, { error: "Not authenticated" }, null);
      }
      token = await user.getIdToken();
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const raw = await response.text();
    parsed = raw ? JSON.parse(raw) : null;
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const parsedRetryAfter = parseInt(retryAfter, 10);
        retryAfterSeconds = Number.isNaN(parsedRetryAfter)
          ? null
          : parsedRetryAfter;
      }
    }
    if (response.status === 401 && authenticated) {
      await handleSessionExpired();
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as T;
}

export type UserSyncResponse = {
  id: string;
  email: string | null;
  name: string | null;
  is_admin: boolean;
  created_at?: string;
};

export async function syncUser(
  firebaseUser?: FirebaseUser,
): Promise<UserSyncResponse> {
  const user = firebaseUser ?? getFirebaseAuth().currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const idToken = await user.getIdToken();
  return apiFetch<UserSyncResponse>("/users/sync", {
    method: "POST",
    body: {},
    idToken,
  });
}

export async function createExperiment(
  raw_idea: string,
  name?: string | null,
): Promise<ExperimentDetail> {
  const body: { raw_idea: string; name?: string } = { raw_idea };
  if (name?.trim()) {
    body.name = name.trim();
  }
  return apiFetch<ExperimentDetail>("/experiments", {
    method: "POST",
    body,
  });
}

export async function getExperiment(id: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}`);
}

export async function renameExperiment(
  id: string,
  name: string,
): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}/name`, {
    method: "PATCH",
    body: { name },
  });
}

export async function getValidationReport(
  id: string,
): Promise<ValidationReport> {
  return apiFetch<ValidationReport>(`/experiments/${id}/validation-report`);
}

export async function listExperiments(options?: {
  archived?: boolean;
}): Promise<ExperimentSummary[]> {
  const params = new URLSearchParams();
  if (options?.archived) {
    params.set("archived", "true");
  }
  const query = params.toString();
  return apiFetch<ExperimentSummary[]>(
    query ? `/experiments?${query}` : "/experiments",
  );
}

export type ChatTurnParams = {
  message: string;
  deep_research: boolean;
  thread_id?: string | null;
  experiment_id?: string | null;
  idempotency_key?: string;
  name?: string | null;
  attachment_ids?: string[];
  signal?: AbortSignal;
};

export type ChatAttachmentUploadItem = {
  id: string;
  filename: string;
  content_kind: string;
  excerpt: string;
  char_count: number;
};

export async function uploadChatAttachments(
  files: File[],
): Promise<ChatAttachmentUploadItem[]> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  let response: Response;
  try {
    response = await fetch(apiUrl("/chat/attachments"), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");
  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = Number.isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  const data = parsed as { attachments: ChatAttachmentUploadItem[] };
  return data.attachments;
}

export async function chatTurn(
  params: ChatTurnParams,
): Promise<ChatTurnResponse> {
  const body: Record<string, unknown> = {
    message: params.message,
    deep_research: params.deep_research,
    thread_id: params.thread_id ?? null,
    experiment_id: params.experiment_id ?? null,
    attachment_ids: params.attachment_ids ?? [],
  };

  if (params.name?.trim()) {
    body.name = params.name.trim();
  }

  if (params.deep_research) {
    body.idempotency_key =
      params.idempotency_key ?? crypto.randomUUID();
  }

  return apiFetch<ChatTurnResponse>("/chat/turn", {
    method: "POST",
    body,
    signal: params.signal,
  });
}

export async function getExperimentChatMessages(
  experimentId: string,
): Promise<ExperimentChatMessagesResponse> {
  return apiFetch<ExperimentChatMessagesResponse>(
    `/chat/experiments/${experimentId}/messages`,
  );
}

export async function editChatMessage(
  threadId: string,
  messageId: string,
  newContent: string,
): Promise<ChatEditTurnResponse> {
  return apiFetch<ChatEditTurnResponse>("/chat/turn/edit", {
    method: "POST",
    body: {
      thread_id: threadId,
      message_id: messageId,
      new_content: newContent,
    },
  });
}

export async function refineExperiment(
  id: string,
  feedback?: string,
): Promise<ExperimentDetail> {
  return apiFetch<ExperimentDetail>(`/experiments/${id}/refine`, {
    method: "POST",
    body: feedback !== undefined ? { feedback } : {},
  });
}

export async function confirmExperiment(id: string): Promise<{
  experiment_id: string;
  status: string;
  status_url: string;
  credits_balance: number;
}> {
  return apiFetch(`/experiments/${id}/confirm`, {
    method: "POST",
    body: {},
  });
}

export async function getResearchStatus(id: string): Promise<ResearchStatus> {
  return apiFetch<ResearchStatus>(`/experiments/${id}/research-status`);
}

export async function getLandingPage(
  experimentId: string,
): Promise<LandingPage> {
  return apiFetch<LandingPage>(`/experiments/${experimentId}/landing-page`);
}

export async function patchLandingPage(
  experimentId: string,
  patch: LandingPagePatch,
  options: { signal?: AbortSignal } = {},
): Promise<LandingPage> {
  return apiFetch<LandingPage>(`/experiments/${experimentId}/landing-page`, {
    method: "PATCH",
    body: patch,
    signal: options.signal,
  });
}

export async function checkLandingPageSlugAvailability(
  experimentId: string,
  slug: string,
): Promise<LandingPageSlugAvailability> {
  const params = new URLSearchParams({ slug });
  return apiFetch<LandingPageSlugAvailability>(
    `/experiments/${experimentId}/landing-page/slug-availability?${params.toString()}`,
  );
}

export async function generateLandingPage(
  id: string,
  options: { template_id: string; page_goal?: string; regeneration_hint?: string } = {
    template_id: "dark-premium",
  },
): Promise<GenerateLandingPageResponse> {
  return apiFetch<GenerateLandingPageResponse>(
    `/experiments/${id}/generate-landing-page`,
    {
      method: "POST",
      body: options,
    },
  );
}

export async function getLandingPageV2(
  experimentId: string,
): Promise<LandingPageV2GenerationStatus> {
  return apiFetch<LandingPageV2GenerationStatus>(
    `/experiments/${experimentId}/landing-page-v2`,
  );
}

export async function generateLandingPageV2(
  experimentId: string,
  body: GenerateLandingPageV2Request = {},
): Promise<GenerateLandingPageV2Response> {
  return apiFetch<GenerateLandingPageV2Response>(
    `/experiments/${experimentId}/landing-page-v2/generate`,
    {
      method: "POST",
      body,
    },
  );
}

/** Canonical runtime API (same backend, preferred route name). */
export async function getLandingPageRuntime(
  experimentId: string,
): Promise<LandingPageV2GenerationStatus> {
  return apiFetch<LandingPageV2GenerationStatus>(
    `/experiments/${experimentId}/landing-page-runtime`,
  );
}

export async function generateLandingPageRuntime(
  experimentId: string,
  body: GenerateLandingPageV2Request = {},
): Promise<GenerateLandingPageV2Response> {
  return apiFetch<GenerateLandingPageV2Response>(
    `/experiments/${experimentId}/landing-page-runtime/generate`,
    {
      method: "POST",
      body,
    },
  );
}

export type MetricsAccessResponse = {
  unlocked: boolean;
};

export type UnlockMetricsResponse = {
  unlocked: boolean;
  already_unlocked: boolean;
  credits_balance: number;
};

export async function getMetricsAccess(
  experimentId: string,
): Promise<MetricsAccessResponse> {
  return apiFetch<MetricsAccessResponse>(
    `/experiments/${experimentId}/metrics-access`,
  );
}

export async function unlockMetrics(
  experimentId: string,
): Promise<UnlockMetricsResponse> {
  return apiFetch<UnlockMetricsResponse>(
    `/experiments/${experimentId}/unlock-metrics`,
    { method: "POST", body: {} },
  );
}

export async function getExperimentAnalytics(
  id: string,
): Promise<ExperimentAnalytics> {
  return apiFetch<ExperimentAnalytics>(`/experiments/${id}/analytics`);
}

export async function getWaitlistSignups(
  experimentId: string,
): Promise<WaitlistSignupsResponse> {
  return apiFetch<WaitlistSignupsResponse>(
    `/experiments/${experimentId}/waitlist`,
  );
}

export async function exportWaitlistCsv(experimentId: string): Promise<void> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }

  const token = await user.getIdToken();
  let response: Response;
  try {
    response = await fetch(apiUrl(`/experiments/${experimentId}/waitlist/export`), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    const parsed = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new ApiError(response.status, parsed, requestId);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "waitlist.csv";
  const match = disposition?.match(/filename="([^"]+)"/);
  if (match?.[1]) {
    filename = match[1];
  }

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export async function getInsightReport(
  id: string,
): Promise<InsightReport> {
  return apiFetch<InsightReport>(`/experiments/${id}/insight-report`);
}

export async function generateInsight(
  id: string,
): Promise<GenerateInsightResponse> {
  return apiFetch<GenerateInsightResponse>(
    `/experiments/${id}/generate-insight`,
    {
      method: "POST",
      body: {},
    },
  );
}

export async function archiveExperiment(
  id: string,
  outcome: FounderDecision | "manual",
): Promise<ArchiveExperimentResponse> {
  return apiFetch<ArchiveExperimentResponse>(`/experiments/${id}/archive`, {
    method: "POST",
    body: { outcome },
  });
}

export async function archiveProject(
  id: string,
): Promise<ArchiveExperimentResponse> {
  return archiveExperiment(id, "manual");
}

export async function unarchiveExperiment(id: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/experiments/${id}/unarchive`, {
    method: "POST",
    body: {},
  });
}

export async function deleteProject(id: string): Promise<DeleteExperimentResponse> {
  return apiFetch<DeleteExperimentResponse>(`/experiments/${id}`, {
    method: "DELETE",
    body: { confirmation: "CONFIRM" },
  });
}

export async function submitPageView(
  slug: string,
  source_tag?: string,
): Promise<void> {
  const body: { slug: string; source_tag?: string } = { slug };
  if (source_tag !== undefined) body.source_tag = source_tag;
  await apiFetch<void>("/analytics/page-view", {
    method: "POST",
    body,
    authenticated: false,
  });
}

export async function submitWaitlistSignup(
  slug: string,
  email: string,
): Promise<void> {
  await apiFetch<void>(`/e/${slug}/waitlist`, {
    method: "POST",
    body: { email },
    authenticated: false,
  });
}

export type PublishProjectResponse = {
  message: string;
  slug: string;
  public_url: string;
};

export type PublicationSummary = {
  id: string;
  slug: string;
  public_url: string;
  is_current: boolean;
  output_version: number;
  cta_mode: string;
  published_at: string;
};

export async function publishProject(
  experimentId: string,
  payload: { slug?: string; cta_mode: string; cta_url?: string },
): Promise<PublishProjectResponse> {
  return apiFetch<PublishProjectResponse>(
    `/experiments/${experimentId}/landing-page/publish`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function listPublications(
  experimentId: string,
): Promise<PublicationSummary[]> {
  return apiFetch<PublicationSummary[]>(
    `/experiments/${experimentId}/landing-page/publications`,
  );
}

export async function uploadProjectLogo(
  experimentId: string,
  file: File,
): Promise<{ logo_url: string; filename: string }> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(
      apiUrl(`/experiments/${experimentId}/landing-page/logo`),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as { logo_url: string; filename: string };
}

export async function uploadSectionImage(
  experimentId: string,
  file: File,
): Promise<{ image_url: string; filename: string }> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new ApiError(401, { error: "Not authenticated" }, null);
  }
  const token = await user.getIdToken();

  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(
      apiUrl(`/experiments/${experimentId}/landing-page/section-image`),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      },
    );
  } catch (err) {
    throw new ApiError(
      0,
      { error: err instanceof Error ? err.message : "Network error" },
      null,
    );
  }

  const requestId = response.headers.get("X-Request-ID");

  let parsed: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    parsed = await response.json();
  } else {
    parsed = await response.text();
  }

  if (!response.ok) {
    let retryAfterSeconds: number | null = null;
    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      if (retryAfter !== null) {
        const retryParsed = parseInt(retryAfter, 10);
        retryAfterSeconds = isNaN(retryParsed) ? null : retryParsed;
      }
    }
    throw new ApiError(response.status, parsed, requestId, retryAfterSeconds);
  }

  return parsed as { image_url: string; filename: string };
}

export type ProductCostRow = {
  cost_category: string;
  label: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type PerProductCostResponse = {
  days_back: number;
  rows: ProductCostRow[];
};

export type DailyCostRow = {
  day: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  tavily_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type ExperimentCostStatsRow = {
  experiment_count: number;
  avg_cost_usd: string;
  min_cost_usd: string;
  max_cost_usd: string;
  median_cost_usd: string;
};

export type CostSummaryResponse = {
  days_back: number;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  tavily_logged_cost_usd: string;
  tavily_estimated_gap_usd: string;
  tavily_total_cost_usd: string;
  tavily_logged_credits: number;
  tavily_estimated_gap_credits: number;
  tavily_unlogged_experiment_count: number;
  llm_call_count: number;
  external_api_call_count: number;
  active_user_count: number;
  experiment_stats: ExperimentCostStatsRow;
  target_cost_per_experiment_usd: string;
  tavily_usd_per_credit: string;
};

export type UserCostInsightRow = {
  user_id: string;
  email: string;
  name: string | null;
  experiment_count: number;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
};

export type ExperimentPhaseCostRow = {
  phase: string;
  label: string;
  source: string;
  cost_usd: string;
  call_count: number;
};

export type UserExperimentCostRow = {
  experiment_id: string;
  label: string;
  name: string | null;
  status: string;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  phases: ExperimentPhaseCostRow[];
};

export type UserExperimentsCostResponse = {
  user_id: string;
  email: string;
  name: string | null;
  days_back: number;
  experiments: UserExperimentCostRow[];
};

export type ProviderCostRow = {
  provider: string;
  source: string;
  cost_usd: string;
  call_count: number;
};

export type PhaseCostRow = {
  phase: string | null;
  llm_cost_usd: string;
  call_count: number;
};

export type TopExperimentCostRow = {
  experiment_id: string;
  label: string;
  total_cost_usd: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
};

export type CostInsightsResponse = {
  days_back: number;
  summary: CostSummaryResponse;
  per_user: UserCostInsightRow[];
  per_provider: ProviderCostRow[];
  per_phase: PhaseCostRow[];
  top_experiments: TopExperimentCostRow[];
};

export type DailyCostResponse = {
  days_back: number;
  rows: DailyCostRow[];
};

export type ExperimentCostResponse = {
  experiment_id: string;
  llm_cost_usd: string;
  external_api_cost_usd: string;
  total_cost_usd: string;
  llm_call_count: number;
  external_api_call_count: number;
  products: ProductCostRow[];
};

export async function getAdminPerProductCost(
  days = 30,
): Promise<PerProductCostResponse> {
  return apiFetch<PerProductCostResponse>(
    `/admin/cost/per-product?days=${days}`,
  );
}

export async function getAdminDailyCost(
  days = 30,
): Promise<DailyCostResponse> {
  return apiFetch<DailyCostResponse>(`/admin/cost/daily?days=${days}`);
}

export async function getAdminExperimentCost(
  experimentId: string,
): Promise<ExperimentCostResponse> {
  return apiFetch<ExperimentCostResponse>(
    `/admin/cost/experiment/${experimentId}`,
  );
}

export async function getAdminCostInsights(
  days = 30,
): Promise<CostInsightsResponse> {
  return apiFetch<CostInsightsResponse>(`/admin/cost/insights?days=${days}`);
}

export async function getAdminUserExperimentsCost(
  userId: string,
  days = 30,
): Promise<UserExperimentsCostResponse> {
  return apiFetch<UserExperimentsCostResponse>(
    `/admin/cost/user/${userId}/experiments?days=${days}`,
  );
}

export type AdminCouponSummary = {
  id: string;
  code: string;
  credits: number;
  enabled: boolean;
  archived_at: string | null;
  max_redemptions: number | null;
  redemption_count: number;
  remaining_redemptions: number | null;
  total_credits_gifted: number;
  total_usd_gifted: string;
  starts_at: string | null;
  ends_at: string | null;
  limit_reached_message: string | null;
  not_yet_active_message: string | null;
  expired_message: string | null;
  disabled_message: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminCouponListResponse = {
  coupons: AdminCouponSummary[];
  total_usd_gifted_all_coupons: string;
};

export type AdminCreateCouponRequest = {
  code: string;
  credits: number;
  enabled?: boolean;
  max_redemptions?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  limit_reached_message?: string | null;
  not_yet_active_message?: string | null;
  expired_message?: string | null;
  disabled_message?: string | null;
};

export type AdminUpdateCouponRequest = {
  credits?: number;
  enabled?: boolean;
  max_redemptions?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  clear_starts_at?: boolean;
  clear_ends_at?: boolean;
  limit_reached_message?: string | null;
  not_yet_active_message?: string | null;
  expired_message?: string | null;
  disabled_message?: string | null;
  clear_limit_reached_message?: boolean;
  clear_not_yet_active_message?: boolean;
  clear_expired_message?: boolean;
  clear_disabled_message?: boolean;
};

export async function getAdminCoupons(
  includeArchived = false,
): Promise<AdminCouponListResponse> {
  const query = includeArchived ? "?include_archived=true" : "";
  return apiFetch<AdminCouponListResponse>(`/admin/coupons${query}`);
}

export async function createAdminCoupon(
  body: AdminCreateCouponRequest,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>("/admin/coupons", {
    method: "POST",
    body,
  });
}

export async function updateAdminCoupon(
  couponId: string,
  body: AdminUpdateCouponRequest,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveAdminCoupon(
  couponId: string,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}/archive`, {
    method: "POST",
  });
}

export async function restoreAdminCoupon(
  couponId: string,
): Promise<AdminCouponSummary> {
  return apiFetch<AdminCouponSummary>(`/admin/coupons/${couponId}/restore`, {
    method: "POST",
  });
}

export async function deleteAdminCoupon(couponId: string): Promise<void> {
  await apiFetch<void>(`/admin/coupons/${couponId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Wallet (Phase 12)
// ---------------------------------------------------------------------------

export type CreditPack = {
  id: string;
  name: string;
  usd_cents: number;
  usd_display: string;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
};

export type WalletBalance = {
  credits_balance: number;
  usd_equivalent: string;
  total_credits_purchased: number;
  total_credits_consumed: number;
  credit_conversion_rate: number;
  has_redeemed_welcome_coupon: boolean;
  packs: CreditPack[];
};

export type CreateWalletOrderResponse = {
  payment_order_id: string;
  pack_id: string;
  pack_name: string;
  usd_cents: number;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
  amount_inr_paise: number;
  currency: string;
  razorpay_key_id: string;
  razorpay_order_id: string;
  receipt: string;
};

export type VerifyWalletPaymentResponse = {
  payment_order_id: string;
  credits_added: number;
  bonus_credits: number;
  new_balance: number;
  already_processed: boolean;
  razorpay_payment_id: string;
  razorpay_order_id: string;
};

export type RedeemCouponResponse = {
  code: string;
  credits_added: number;
  new_balance: number;
};

export type WalletTransactionType =
  | "TOPUP"
  | "BONUS"
  | "COUPON"
  | "SERVICE_USAGE"
  | "REFUND"
  | "ADMIN_ADJUSTMENT";

export type WalletTransaction = {
  id: string;
  type: WalletTransactionType;
  credits: number;
  title: string;
  detail: string | null;
  reference: string | null;
  created_at: string;
  balance_after: number;
  experiment_id: string | null;
  experiment_name: string | null;
};

export type WalletTransactionsResponse = {
  transactions: WalletTransaction[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  credits_balance: number;
  total_credits_purchased: number;
  total_credits_consumed: number;
};

export async function getWallet(): Promise<WalletBalance> {
  return apiFetch<WalletBalance>("/wallet");
}

export async function getWalletTransactions(
  options: { limit?: number; offset?: number } = {},
): Promise<WalletTransactionsResponse> {
  const params = new URLSearchParams();
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options.offset !== undefined) {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  return apiFetch<WalletTransactionsResponse>(
    `/wallet/transactions${query ? `?${query}` : ""}`,
  );
}

export async function createWalletOrder(
  packId: string,
): Promise<CreateWalletOrderResponse> {
  return apiFetch<CreateWalletOrderResponse>("/wallet/orders", {
    method: "POST",
    body: { packId },
  });
}

export async function verifyWalletPayment(body: {
  razorpayPaymentId: string;
  razorpayOrderId: string;
  razorpaySignature: string;
}): Promise<VerifyWalletPaymentResponse> {
  return apiFetch<VerifyWalletPaymentResponse>("/wallet/payments/verify", {
    method: "POST",
    body,
  });
}

export async function redeemWalletCoupon(
  code: string,
): Promise<RedeemCouponResponse> {
  return apiFetch<RedeemCouponResponse>("/wallet/coupons/redeem", {
    method: "POST",
    body: { code },
  });
}
```

### `lib/types.ts`

```typescript
export type PageGoal =
  | "waitlist"
  | "launch"
  | "app_install"
  | "demo_booking"
  | "investor_teaser"
  | "paid_ads";

export interface CopyJson {
  hero?: HeroCopy;
  problem?: { heading: string; body: string };
  features?: FeatureCopy[];
  comparison?: ComparisonCopy;
  proof?: { headline: string; elements: string[] };
  faq?: FaqItem[];
  cta?: { heading: string; subheading: string; button: string };
  pricing?: unknown;
  [key: string]: unknown;
}

export interface HeroCopy {
  headline: string;
  subheadline: string;
  cta: string;
}

export interface FeatureCopy {
  title: string;
  description: string;
}

export interface ComparisonCopy {
  metric_label: string;
  competitor_name: string;
  our_features: string[];
  competitor_features: string[];
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface PageTheme {
  primary_color?: string;
  accent_color?: string;
  background_color?: string;
  text_color?: string;
  font_family?: string;
  style?: string;
}

export interface UserColorPalette {
  preset: string;
  accent: string;
  background: string;
  foreground: string;
}

export type SurfaceTexture = "none" | "grain" | "paper" | "dot-grid" | "linen";

export type HeroGlow = "off" | "soft" | "bold";

export type GradientStyle = "flat" | "radial" | "mesh-warm" | "mesh-cool";

export interface PageSurface {
  texture?: SurfaceTexture;
  /** @deprecated Use hero_glow_intensity (0–100). Migrated in resolveSurface(). */
  hero_glow?: HeroGlow;
  gradient_style?: GradientStyle;
  /** 0 = off, 100 = strongest hero spotlight */
  hero_glow_intensity?: number;
  /** 0–100; only applies when texture is not "none" */
  texture_intensity?: number;
  /** 0–100; only applies when gradient_style is not "flat" */
  gradient_intensity?: number;
}

export interface PageJson {
  template_id?: string;
  template_name?: string;
  color_mode?: "dark" | "light";
  color_palette?: Partial<UserColorPalette>;
  surface?: PageSurface;
  branding?: {
    icon_mode?: "initials" | "url" | "emoji" | "mark";
    logo_url?: string;
    logo_emoji?: string;
    logo_alt?: string;
    /** Logo mark scale (%). Default 100. Typical range 60–160. */
    logo_scale?: number;
  };
  /** Template section image slots → hosted image URLs (editor uploads). */
  section_images?: Record<string, string>;
  theme?: PageTheme;
  sections?: Array<{ type: string; content: unknown }>;
  meta?: {
    generation_id?: string;
    generated_at?: string;
    regeneration_hint?: string | null;
  };
}

export const PAGE_GOALS: {
  id: PageGoal;
  label: string;
  description: string;
}[] = [
  {
    id: "waitlist",
    label: "Waitlist",
    description: "Capture early interest with trust-first messaging",
  },
  {
    id: "launch",
    label: "MVP Launch",
    description: "Announce your product with benefit-led conversion copy",
  },
  {
    id: "app_install",
    label: "App Install",
    description: "Drive mobile downloads with friction-reducing proof",
  },
  {
    id: "demo_booking",
    label: "Demo Booking",
    description: "Book sales calls with authority and objection handling",
  },
  {
    id: "investor_teaser",
    label: "Investor Teaser",
    description: "Summarize upside, traction signals, and market white-space",
  },
  {
    id: "paid_ads",
    label: "Paid Ads LP",
    description: "Single-offer pages optimized for paid traffic conversion",
  },
];

export const REGENERATABLE_SECTIONS = [
  "hero",
  "problem",
  "features",
  "comparison",
  "proof",
  "objections",
  "faq",
  "pricing",
  "cta",
] as const;

export type RegenerableSection = (typeof REGENERATABLE_SECTIONS)[number];

// --- Backend-matching experiment types ---

export interface RefinedIdea {
  refined_one_liner: string;
  target_audience: string;
  value_proposition: string;
  risks: string[];
  headline: string;
  subheadline: string;
  cta_text: string;
}

export interface ExperimentCardStats {
  page_views: number;
  waitlist_signups: number;
}

export interface ExperimentSummary {
  id: string;
  slug: string | null;
  name?: string | null;
  raw_idea: string;
  status: string;
  created_at: string;
  updated_at: string;
  card_stats?: ExperimentCardStats | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  refined_idea: RefinedIdea | null;
  landing_page: LandingPageData | null;
  validation_report_id: string | null;
  insight_report_id: string | null;
}

export interface GenerateLandingPageRequest {
  page_goal?: string;
  template_id?: string;
}

export interface GenerateLandingPageResponse {
  experiment_id: string;
  status: string;
}

export interface JobStatus {
  id: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
}

export interface ResearchStatus {
  status: string;
  phase_label: string | null;
  phases_completed: string[];
  last_updated_at: string;
  error_detail: string | null;
}

export interface ExperimentValidationReportSummary {
  overall_recommendation: string | null;
  total_finding_count: number;
  total_citation_count: number;
}

/** GET /experiments/{id} response shape */
export interface Experiment {
  id: string;
  name?: string | null;
  raw_idea?: string | null;
  status: string;
  thread_id?: string | null;
  validation_report: ExperimentValidationReportSummary | null;
}

// --- Clarifying question block (refinement pre-research) ---

export type ClarifyingSelectionMode = "single" | "multiple";

export interface ClarifyingQuestion {
  question: string;
  selection_mode: ClarifyingSelectionMode;
  options: string[];
}

export interface ClarifyingQuestionAnswer {
  selectedOptions: string[];
  otherText: string;
}

export interface ChatHistoryMessage {
  id: string;
  role: ChatRole;
  content: string;
  turn_kind: ChatTurnKind | null;
  clarifying_questions?: ClarifyingQuestion[] | null;
  created_at: string;
}

export interface ExperimentChatMessagesResponse {
  thread_id: string | null;
  experiment_id: string;
  messages: ChatHistoryMessage[];
}

export interface Citation {
  url: string;
  title: string;
  source_domain: string;
  accessed_at: string;
}

export interface Finding {
  question_id: string;
  claim: string;
  evidence_summary: string;
  citations: Citation[];
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface SectionScore {
  section_id:
    | "market"
    | "competition"
    | "distribution"
    | "regulatory"
    | "risk"
    | "research";
  label: string;
  score: number;
  rationale?: string | null;
  pros?: string[];
  cons?: string[];
}

export interface QuestionFindings {
  question_id: string;
  question: string;
  findings: Finding[];
  evidence_gap: string | null;
  score?: number | null;
}

export interface CompetitorMention {
  name: string;
  description: string;
  positioning_vs_idea: string;
  citations: Citation[];
}

export type OverallRecommendation =
  | "proceed"
  | "iterate"
  | "pivot"
  | "kill"
  | "too_vague_to_recommend";

export interface ValidationReport {
  executive_summary: string;
  questions_and_findings: QuestionFindings[];
  competitors: CompetitorMention[];
  market_signals: string;
  distribution_signals: string | null;
  regulatory_signals: string | null;
  risks_assessment: string;
  overall_recommendation: OverallRecommendation;
  recommendation_rationale: string;
  research_limitations: string;
  rubric_version_used: string;
  section_scores?: SectionScore[];
  overall_score?: number | null;
}

export interface LandingPageData {
  copy_json: CopyJson;
  page_json: PageJson;
}

/** GET /experiments/{id}/landing-page response */
export interface LandingPage {
  id: string;
  experiment_id: string;
  slug: string;
  template_id: string;
  copy_json: CopyJson;
  page_json: PageJson;
  headline: string;
  subheadline: string | null;
  live_at: string | null;
  output_version?: number;
}

export type LandingPagePatch = {
  copy_json?: CopyJson;
  page_json?: PageJson;
  template_id?: string;
  slug?: string;
};

export interface LandingPageSlugAvailability {
  slug: string;
  available: boolean;
  taken_by_live: boolean;
  message: string | null;
}

// --- Chat types (POST /chat/turn, ADR 0019) ---

export type ChatRole = "user" | "assistant";

export type ChatTurnKind =
  | "normal_chat"
  | "discuss"
  | "refinement_clarify"
  | "refinement_finalize"
  | "dispatch_announce"
  | "pipeline_progress"
  | "pipeline_complete"
  | "pipeline_failed";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp?: string;
  turnKind?: ChatTurnKind | null;
  clarifyingQuestions?: ClarifyingQuestion[];
}

export interface ChatEditTurnResponse {
  thread_id: string;
  edited_message_id: string;
  message_id: string;
  experiment_id: string | null;
  assistant_message: string;
  turn_kind: ChatTurnKind;
  clarifying_dimension: string | null;
  clarifying_questions?: ClarifyingQuestion[];
  pipeline_dispatched: boolean;
  dispatched_at: string | null;
  experiment_status: string | null;
  research_error_detail: string | null;
  messages: ChatHistoryMessage[];
}

export interface ChatTurnResponse {
  thread_id: string;
  message_id: string;
  experiment_id: string | null;
  assistant_message: string;
  turn_kind: ChatTurnKind;
  clarifying_dimension: string | null;
  clarifying_questions?: ClarifyingQuestion[];
  pipeline_dispatched: boolean;
  dispatched_at: string | null;
  experiment_status: string | null;
  research_error_detail: string | null;
}

// --- Insight & analytics types (ADR 0021) ---

export type InsightRecommendationType = "proceed" | "iterate" | "pivot" | "kill";

export type TakeawaySourceType = "BEHAVIORAL" | "COGNITIVE" | "SYNTHESIZED";

export type FounderDecision = InsightRecommendationType;

export interface WaitlistSignup {
  id: string;
  email: string;
  source_tag: string | null;
  geo_city?: string | null;
  geo_region?: string | null;
  geo_country?: string | null;
  created_at: string;
}

export interface WaitlistSignupsResponse {
  signups: WaitlistSignup[];
  total: number;
}

export interface SignupLocationBucket {
  city: string | null;
  region: string | null;
  country: string | null;
  count: number;
}

export interface ExperimentAnalytics {
  total_page_views: number;
  total_signups: number;
  unique_visitors: number;
  conversion_rate: number;
  views_by_source: Record<string, number>;
  signups_by_source: Record<string, number>;
  conversion_rate_by_source: Record<string, number>;
  signups_by_location: SignupLocationBucket[];
  days_live: number;
  warm_network_bias_index?: number;
}

export interface ResearchTakeaway {
  claim: string;
  cited_finding_ids: string[];
  source_type: TakeawaySourceType;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface TrafficSummary {
  narrative: string;
  headline_metric: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
  source_type: TakeawaySourceType;
}

export interface ConversionSourceCommentary {
  source_name: string;
  views: number;
  signups: number;
  conversion_rate: number;
  commentary: string;
  confidence: "high" | "medium" | "low";
}

export interface ConversionBySource {
  per_source: ConversionSourceCommentary[];
  warm_network_bias_commentary: string;
  confidence: "high" | "medium" | "low";
  confidence_rationale: string;
}

export interface InsightReport {
  traffic_summary: TrafficSummary;
  conversion_by_source: ConversionBySource;
  research_takeaways: ResearchTakeaway[];
  recommendation_type: InsightRecommendationType;
  recommendation: string;
  recommendation_confidence: "high" | "medium" | "low";
  recommendation_rationale: string;
  what_would_change_this: string;
}

export interface GenerateInsightResponse {
  experiment_id: string;
  status: string;
  credits_balance: number;
}

export interface ArchiveExperimentResponse {
  experiment_id: string;
  status: string;
}

export interface DeleteExperimentResponse {
  experiment_id: string;
  deleted: boolean;
}
```

## 8. Design system status

- **Formal design system:** No Storybook, no Radix/shadcn component library. Design is a **de facto token system** in `frontend/app/globals.css` (`--fv-*` CSS variables) mapped into Tailwind via `frontend/tailwind.config.ts` (`fv.*` color keys).
- **Typography:** Inter + DM Mono via `next/font` in `app/layout.tsx`.
- **Component primitives:** Lightweight shared components under `frontend/components/ui/` (EmptyState, ErrorBanner, LoadingState, PageHeader, ToastProvider, TypeConfirmDialog) plus many utility classes in `globals.css` (`.fv-btn-primary`, `.fv-card`, `.fv-q-option`, `.fv-stage-tab`, report badges, etc.).
- **Refinement-specific styling:** `components/refinement/refinement-ascent.css` and `refinement-thread.css` layered on top of global tokens.
- **Report reader styling:** `components/research/report-canvas.css` and `report-score-section.css`.
- **Storybook / component gallery:** DOES NOT EXIST.
- **Frontend tests:**
  - `frontend/lib/__tests__/report-text.test.ts` (Vitest)
  - `frontend/vitest.config.ts`

## 9. Known frontend pain points

- **Dual report viewers:** `ValidationReportViewer.tsx` and `ReportCanvas.tsx` both render validation reports with overlapping section logic; `ExperimentDetailPanel` / stage routing may show one or the other depending on context — risk of UI drift.
- **Refinement demo vs live paths:** `components/refinement-demos/` duplicates live refinement thread components (`RefinementThreadMessage`, `PressureTestSection`) for `/refinement-demos` — styling changes must be applied in two places or demos diverge from production.
- **Clarifying question wizard state is local:** `ClarifyingQuestionBlock.tsx` owns carousel index + answers in component state; no shared hook (`useRefineChat` / `useChatThread` do not exist). `ChatInterface.tsx` is the de facto state machine (~900+ lines) mixing refine chat, research dispatch, paywall gates, and experiment lifecycle.
- **No `ExperimentContext`:** experiment state lives in `ExperimentDetailPanel.tsx` via `useState` + polling `getExperiment()`; child stage panels receive props/callbacks rather than a shared context — similar data refetched in multiple tabs.
- **API types monolith:** `lib/types.ts` holds refinement, research, landing, wallet, and chat types in one large file; frontend rendering assumptions can drift from backend schema without compile-time coupling on nested report fields.
- **Loading states uneven:** `ClarifyingQuestionsLoading.tsx` covers pending clarify turns; report reader loading is split between `ValidationReportPanel.tsx` polling and inline spinners in `ReportCanvas.tsx` — no unified skeleton for full report load.
- **Research dispatch split:** auto-dispatch after finalize in `ChatInterface.tsx` plus manual `confirmExperiment()` in `ExperimentDetailPanel.tsx` / `ValidationResearchPrompt.tsx` — two entry points to start research.
- **Legacy CSS aliases:** `globals.css` duplicates clarifying-option styles (`.fv-q-option` vs `.q-option`) and message bubbles (`.fv-msg-*` vs `.msg-bubble-*`) suggesting incremental redesign without cleanup.
- **Uncommitted report export work:** `ValidationReportExportMenu.tsx` is new/untracked; `validation-report-export.ts` and `report-text.ts` have large in-progress diffs — export markdown path may not match rendered report sections yet.

## 10. Recent uncommitted frontend work

### `git status -- frontend`

```text
On branch feature/enhancements
Your branch is up to date with 'origin/feature/enhancements'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   frontend/components/research/ReportCanvas.tsx
	modified:   frontend/lib/api.ts
	modified:   frontend/lib/report-text.ts
	modified:   frontend/lib/validation-report-export.ts
	modified:   frontend/package-lock.json
	modified:   frontend/package.json

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	frontend/app/(dashboard)/experiment/[id]/landing-page-runtime/
	frontend/app/(dashboard)/experiment/[id]/landing-page-v2/
	frontend/components/landing-runtime-v2/
	frontend/components/research/ValidationReportExportMenu.tsx
	frontend/lib/__tests__/
	frontend/lib/landing-page-v2-types.ts
	frontend/vitest.config.ts

no changes added to commit (use "git add" and/or "git commit -a")
```

### `git diff HEAD --stat -- frontend`

```text
 frontend/components/research/ReportCanvas.tsx |   35 +-
 frontend/lib/api.ts                           |   48 +
 frontend/lib/report-text.ts                   |   17 +-
 frontend/lib/validation-report-export.ts      |  243 +-
 frontend/package-lock.json                    | 3324 ++++++++++++++++++-------
 frontend/package.json                         |    6 +-
 6 files changed, 2716 insertions(+), 957 deletions(-)
```

### `git diff HEAD -- frontend` (4450 lines — exceeds 500; omitted)

Diff is too large to inline. Run `git diff HEAD -- frontend` locally for full patch.

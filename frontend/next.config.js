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

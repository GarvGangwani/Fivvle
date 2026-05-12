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

const csp = isDev
  ? "default-src 'self'; " +
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; " +
    "connect-src 'self' http://localhost:8000 ws://localhost:3000 https://*.googleapis.com https://*.firebaseapp.com https://*.firebaseio.com"
  : "default-src 'self'; " +
    "script-src 'self' 'unsafe-inline'; " +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; " +
    "connect-src 'self' https://*.googleapis.com https://*.firebaseapp.com https://*.firebaseio.com";

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

module.exports = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

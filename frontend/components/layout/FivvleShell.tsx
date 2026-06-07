"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { FivvleLogo } from "./FivvleLogo";

const TABS = [
  { id: "validate", href: "/", label: "Validate" },
  { id: "host", href: "/landing-page-generator", label: "Host" },
  { id: "distribute", href: "/distribute", label: "Distribute" },
] as const;

function tabActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

interface FivvleShellProps {
  children: ReactNode;
  /** Full-height body below header (validate chat layout). */
  fullHeight?: boolean;
}

export function FivvleShell({ children, fullHeight = false }: FivvleShellProps) {
  const pathname = usePathname();

  return (
    <div
      className="min-h-screen text-[var(--fv-text)]"
      style={{ background: "var(--fv-bg)", fontFamily: "var(--font-sans)" }}
    >
      <header
        className="sticky top-0 z-50 flex h-[58px] items-center justify-between border-b px-6"
        style={{
          borderColor: "rgba(255,255,255,0.06)",
          background: "rgba(8,12,20,0.9)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Link href="/" className="flex items-center gap-2.5 no-underline">
          <FivvleLogo size={30} className="rounded-lg" />
          <span className="text-[15px] font-semibold tracking-tight text-[var(--fv-text)]">
            Fivvle
          </span>
        </Link>

        <nav
          className="flex rounded-xl border p-1"
          style={{
            background: "rgba(255,255,255,0.04)",
            borderColor: "rgba(255,255,255,0.08)",
          }}
        >
          {TABS.map((tab) => (
            <Link
              key={tab.id}
              href={tab.href}
              className={`fv-tab-pill no-underline ${
                tabActive(pathname, tab.href) ? "fv-tab-pill-active" : ""
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </nav>

        <p className="text-[13px] text-[var(--fv-text-muted)]">
          <span className="text-[var(--fv-text-soft)]">Good evening,</span>{" "}
          <span className="font-medium text-[var(--fv-accent)]">Founder</span>
        </p>
      </header>

      <div className={fullHeight ? "h-[calc(100vh-58px)] overflow-hidden" : ""}>
        {children}
      </div>
    </div>
  );
}

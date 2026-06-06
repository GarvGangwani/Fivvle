"use client";

import type { ReactNode } from "react";
import { resolveCtaHref, type CtaConfig } from "@/lib/cta-config";

interface CtaActionProps {
  config?: CtaConfig;
  scrollTarget?: string;
  className?: string;
  children: ReactNode;
  as?: "button" | "link";
}

export function CtaAction({
  config,
  scrollTarget = "#cta",
  className,
  children,
  as = "button",
}: CtaActionProps) {
  const href = resolveCtaHref(config, scrollTarget);
  const isExternal = config?.mode === "external" && config.url;

  if (isExternal || as === "link") {
    return (
      <a
        href={href}
        className={className}
        {...(isExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      >
        {children}
      </a>
    );
  }

  return (
    <a href={href} className={className}>
      {children}
    </a>
  );
}

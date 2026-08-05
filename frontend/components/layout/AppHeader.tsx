import Link from "next/link";
import type { ReactNode } from "react";
import { FivvleLogo } from "./FivvleLogo";
interface AppHeaderProps {
  badge?: string;
  actions?: ReactNode;
}

export function AppHeader({ badge, actions }: AppHeaderProps) {
  return (
    <header className="border-b border-white/10 bg-black/40 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2.5 no-underline">
            <FivvleLogo size={28} className="rounded-lg" />
            <span className="text-lg font-semibold tracking-tight text-white">
              Fivvle
            </span>
          </Link>          {badge && (
            <span className="rounded-full border border-accent/30 bg-accent-muted px-3 py-1 text-xs font-medium text-accent">
              {badge}
            </span>
          )}
        </div>
        {actions}
      </div>
    </header>
  );
}

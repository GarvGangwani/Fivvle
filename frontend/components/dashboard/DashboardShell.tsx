"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { WalletProvider } from "@/lib/wallet-context";
import { AppSideRail } from "./AppSideRail";
import { AppTopNav } from "./AppTopNav";
import { GlobalSearchModal } from "./GlobalSearchModal";
import { SearchModalProvider, useSearchModal } from "./search-modal-context";

// AIComposerPill removed — moves to experiment page in Step 5. Keep the component file.

interface DashboardShellProps {
  children: ReactNode;
}

function SearchKeyboardShortcuts() {
  const { openSearch, closeSearch } = useSearchModal();

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openSearch();
      }
      if (event.key === "Escape") {
        closeSearch();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [openSearch, closeSearch]);

  return null;
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <WalletProvider>
      <SearchModalProvider>
        <SearchKeyboardShortcuts />
        <div className="min-h-screen bg-canvas-bg text-ink-primary">
          <AppTopNav />
          <AppSideRail />
          <main className="min-h-screen pt-16 md:ml-28 md:pl-gutter md:pr-gutter md:pb-gutter">
            {children}
          </main>
          <GlobalSearchModal />
        </div>
      </SearchModalProvider>
    </WalletProvider>
  );
}

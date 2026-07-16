"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ProfileAvatar } from "./ProfileAvatar";
import { useSearchModal } from "./search-modal-context";

export function AppSideRail() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { openSearch } = useSearchModal();

  const homeActive = pathname === "/";
  const newActive = pathname === "/new" || pathname.startsWith("/new/");
  const settingsActive =
    pathname === "/settings" || pathname.startsWith("/settings/");

  // notifications feature deferred — tracked-work #33

  const iconClass = (active: boolean) =>
    `flex h-12 w-12 items-center justify-center rounded-sm border-2 transition-colors ${
      active
        ? "border-border-master bg-brand-primary text-ink-inverse shadow-brutal-sm"
        : "border-transparent text-ink-secondary hover:border-border-master hover:bg-surface-elevated hover:text-ink-primary"
    }`;

  return (
    <aside
      className="fixed left-0 top-16 z-40 hidden h-[calc(100vh-4rem)] w-28 flex-col items-center border-r-2 border-border-master bg-canvas-bg py-6 md:flex"
      aria-label="App navigation"
    >
      <div className="mb-8 pointer-events-none">
        <ProfileAvatar
          photoURL={user?.photoURL}
          displayName={user?.displayName ?? user?.email}
          size="md"
        />
      </div>

      <nav className="flex flex-1 flex-col items-center gap-2">
        <Link
          href="/"
          className={`${iconClass(homeActive)} no-underline`}
          aria-label="Home"
          title="Home"
          aria-current={homeActive ? "page" : undefined}
        >
          <span className="material-symbols-outlined" aria-hidden>
            home
          </span>
        </Link>
        <Link
          href="/new"
          className={`${iconClass(newActive)} no-underline`}
          aria-label="Start new validation"
          title="Start new validation"
        >
          <span className="material-symbols-outlined" aria-hidden>
            rocket_launch
          </span>
        </Link>
        <button
          type="button"
          className={iconClass(false)}
          aria-label="Search"
          title="Search"
          onClick={openSearch}
        >
          <span className="material-symbols-outlined" aria-hidden>
            search
          </span>
        </button>
        <Link
          href="/settings"
          className={`${iconClass(settingsActive)} no-underline`}
          aria-label="Settings"
          title="Settings"
        >
          <span className="material-symbols-outlined" aria-hidden>
            settings
          </span>
        </Link>
      </nav>
    </aside>
  );
}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Home, Monitor, Moon, Rocket, Search, Settings, Sun } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { usePreferences, type ThemeMode } from "@/lib/preferences-context";
import { ProfileAvatar } from "./ProfileAvatar";
import { useSearchModal } from "./search-modal-context";

const THEME_CYCLE: ThemeMode[] = ["light", "dark", "system"];

function nextThemeMode(mode: ThemeMode): ThemeMode {
  const index = THEME_CYCLE.indexOf(mode);
  return THEME_CYCLE[(index + 1) % THEME_CYCLE.length] ?? "light";
}

function themeLabel(mode: ThemeMode): string {
  if (mode === "light") return "Light";
  if (mode === "dark") return "Dark";
  return "System";
}

function ThemeIcon({ mode }: { mode: ThemeMode }) {
  if (mode === "light") return <Sun className="h-4 w-4" aria-hidden />;
  if (mode === "dark") return <Moon className="h-4 w-4" aria-hidden />;
  return <Monitor className="h-4 w-4" aria-hidden />;
}

function isCanvasRoute(pathname: string): boolean {
  return pathname.startsWith("/experiment/");
}

function useNavActiveState() {
  const pathname = usePathname();
  return {
    pathname,
    homeActive: pathname === "/",
    experimentsActive:
      pathname === "/experiments" ||
      pathname.startsWith("/experiments/") ||
      pathname.startsWith("/experiment/"),
  };
}

type AccountMenuProps = {
  /** Avatar hit-area size in px (square). */
  size?: number;
  dropdownAlign?: "left" | "right";
};

function AccountMenu({ size = 40, dropdownAlign = "right" }: AccountMenuProps) {
  const { user, logOut } = useAuth();
  const { themeMode, setThemeMode } = usePreferences();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (target && rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function handleSignOut() {
    setOpen(false);
    await logOut();
    window.location.href = "/login";
  }

  const dropdownItemClass =
    "w-full text-left px-4 py-2 text-sm text-[var(--fv-text)] hover:bg-[var(--fv-surface-2)] transition-colors no-underline flex items-center gap-2";

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className="flex items-center justify-center overflow-hidden rounded-full border-2 border-border-master bg-[var(--fv-surface-2)] p-0"
        style={{ width: size, height: size }}
        aria-label="Account menu"
        aria-expanded={open}
        aria-haspopup="menu"
        title="Account"
        onClick={() => setOpen((prev) => !prev)}
      >
        <ProfileAvatar
          photoURL={user?.photoURL}
          displayName={user?.displayName ?? user?.email}
          size="sm"
          className="!h-full !w-full !bg-transparent !p-0"
        />
      </button>

      {open ? (
        <div
          role="menu"
          className={`absolute top-12 min-w-[200px] rounded-md border-2 border-border-master bg-[var(--fv-surface-card)] py-2 shadow-brutal-md ${
            dropdownAlign === "right" ? "right-0" : "left-0"
          }`}
        >
          <p className="px-4 py-2 text-xs text-[var(--fv-text-muted)]">
            {user?.email ?? "Signed in"}
          </p>

          <div className="my-1 border-t border-[var(--fv-border)]" />

          <button
            type="button"
            role="menuitem"
            className={dropdownItemClass}
            onClick={() => {
              setOpen(false);
              router.push("/settings");
            }}
          >
            <Settings className="h-4 w-4 shrink-0" aria-hidden />
            Settings
          </button>

          <button
            type="button"
            role="menuitem"
            className={dropdownItemClass}
            onClick={() => setThemeMode(nextThemeMode(themeMode))}
          >
            <ThemeIcon mode={themeMode} />
            Theme: {themeLabel(themeMode)}
          </button>

          <div className="my-1 border-t border-[var(--fv-border)]" />

          <button
            type="button"
            role="menuitem"
            className={dropdownItemClass}
            onClick={() => void handleSignOut()}
          >
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}

function barItemClass(active: boolean) {
  return `flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors no-underline ${
    active
      ? "text-[var(--fv-accent)] bg-[var(--fv-accent-muted)]"
      : "text-[var(--fv-text-muted)] hover:text-[var(--fv-text)] hover:bg-[var(--fv-surface-2)]"
  }`;
}

function DashboardNavBar() {
  const { homeActive, experimentsActive } = useNavActiveState();
  const { openSearch } = useSearchModal();

  return (
    <header className="fixed top-0 left-0 right-0 z-30 flex h-16 items-center justify-between border-b-2 border-border-master bg-[var(--fv-surface-card)] px-8">
      <Link
        href="/"
        className="font-display text-lg font-black uppercase tracking-tight text-[var(--fv-text)] no-underline"
      >
        FIVVLE
      </Link>

      <nav
        className="absolute left-1/2 flex -translate-x-1/2 items-center gap-1"
        aria-label="App sections"
      >
        <Link
          href="/"
          className={barItemClass(homeActive)}
          aria-current={homeActive ? "page" : undefined}
        >
          <Home className="h-4 w-4 shrink-0" aria-hidden />
          Home
        </Link>
        <Link
          href="/experiments"
          className={barItemClass(experimentsActive)}
          aria-current={experimentsActive ? "page" : undefined}
        >
          <Rocket className="h-4 w-4 shrink-0" aria-hidden />
          Experiments
        </Link>
        <button
          type="button"
          className={barItemClass(false)}
          aria-label="Search"
          onClick={openSearch}
        >
          <Search className="h-4 w-4 shrink-0" aria-hidden />
          Search
        </button>
      </nav>

      <AccountMenu size={40} dropdownAlign="right" />
    </header>
  );
}

function canvasItemClass(active: boolean) {
  return `flex items-center justify-center rounded-md p-2.5 transition-colors no-underline ${
    active
      ? "text-[var(--fv-accent)] bg-[var(--fv-accent-muted)]"
      : "text-[var(--fv-text-muted)] hover:text-[var(--fv-text)] hover:bg-[var(--fv-surface-2)]"
  }`;
}

function CanvasFloatingNav() {
  const { homeActive, experimentsActive } = useNavActiveState();
  const { openSearch } = useSearchModal();

  return (
    <>
      <Link
        href="/"
        className="fixed top-6 left-6 z-30 font-display text-lg font-black uppercase tracking-tight text-[var(--fv-text)] no-underline"
      >
        FIVVLE
      </Link>

      <nav
        className="fixed top-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-1 rounded border-2 border-border-master bg-[var(--fv-surface-card)] px-1 py-1 shadow-brutal-sm"
        aria-label="App sections"
      >
        <Link
          href="/"
          className={canvasItemClass(homeActive)}
          aria-current={homeActive ? "page" : undefined}
          aria-label="Home"
          title="Home"
        >
          <Home className="h-5 w-5 shrink-0" aria-hidden />
        </Link>
        <Link
          href="/experiments"
          className={canvasItemClass(experimentsActive)}
          aria-current={experimentsActive ? "page" : undefined}
          aria-label="Experiments"
          title="Experiments"
        >
          <Rocket className="h-5 w-5 shrink-0" aria-hidden />
        </Link>
        <button
          type="button"
          className={canvasItemClass(false)}
          aria-label="Search"
          title="Search"
          onClick={openSearch}
        >
          <Search className="h-5 w-5 shrink-0" aria-hidden />
        </button>

        <div
          className="mx-1 h-6 border-l border-[var(--fv-border)]"
          aria-hidden
        />

        <AccountMenu size={40} dropdownAlign="right" />
      </nav>
    </>
  );
}

/** Route-dispatched app chrome: full bar on dashboard, floating pill on canvas. */
export function FloatingAppNav() {
  const pathname = usePathname();
  return isCanvasRoute(pathname) ? <CanvasFloatingNav /> : <DashboardNavBar />;
}

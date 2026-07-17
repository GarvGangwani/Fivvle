"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeMode = "light" | "dark" | "system";

const THEME_STORAGE_KEY = "fivvle-theme";
const REDUCED_MOTION_STORAGE_KEY = "fivvle-reduced-motion";

function readThemeMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    /* ignore */
  }
  return "system";
}

function readReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(REDUCED_MOTION_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "light") return "light";
  if (mode === "dark") return "dark";
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyDocumentPreferences(
  mode: ThemeMode,
  reducedMotion: boolean,
): "light" | "dark" {
  const resolved = resolveTheme(mode);
  document.documentElement.setAttribute("data-theme", resolved);
  document.documentElement.setAttribute(
    "data-reduced-motion",
    reducedMotion ? "true" : "false",
  );
  return resolved;
}

interface PreferencesContextValue {
  themeMode: ThemeMode;
  resolvedTheme: "light" | "dark";
  reducedMotion: boolean;
  setThemeMode: (mode: ThemeMode) => void;
  setReducedMotion: (enabled: boolean) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  const [reducedMotion, setReducedMotionState] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const mode = readThemeMode();
    const motion = readReducedMotion();
    setThemeModeState(mode);
    setReducedMotionState(motion);
    setResolvedTheme(applyDocumentPreferences(mode, motion));
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    setResolvedTheme(applyDocumentPreferences(themeMode, reducedMotion));
    try {
      localStorage.setItem(THEME_STORAGE_KEY, themeMode);
    } catch {
      /* ignore */
    }
  }, [themeMode, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    applyDocumentPreferences(themeMode, reducedMotion);
    try {
      localStorage.setItem(
        REDUCED_MOTION_STORAGE_KEY,
        reducedMotion ? "true" : "false",
      );
    } catch {
      /* ignore */
    }
  }, [reducedMotion, themeMode, hydrated]);

  useEffect(() => {
    if (!hydrated || themeMode !== "system") return;

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      setResolvedTheme(applyDocumentPreferences("system", reducedMotion));
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [themeMode, reducedMotion, hydrated]);

  const setThemeMode = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode);
  }, []);

  const setReducedMotion = useCallback((enabled: boolean) => {
    setReducedMotionState(enabled);
  }, []);

  const value = useMemo(
    () => ({
      themeMode,
      resolvedTheme,
      reducedMotion,
      setThemeMode,
      setReducedMotion,
    }),
    [themeMode, resolvedTheme, reducedMotion, setThemeMode, setReducedMotion],
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error("usePreferences must be used within PreferencesProvider");
  }
  return ctx;
}

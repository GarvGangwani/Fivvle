"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  type RefObject,
} from "react";

type ComposerFocusContextValue = {
  inputRef: RefObject<HTMLInputElement | null>;
  focusComposer: () => void;
};

const ComposerFocusContext = createContext<ComposerFocusContextValue | null>(
  null,
);

export function ComposerFocusProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const focusComposer = useCallback(() => {
    inputRef.current?.focus();
    inputRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  const value = useMemo(
    () => ({ inputRef, focusComposer }),
    [focusComposer],
  );

  return (
    <ComposerFocusContext.Provider value={value}>
      {children}
    </ComposerFocusContext.Provider>
  );
}

export function useComposerFocus(): ComposerFocusContextValue {
  const ctx = useContext(ComposerFocusContext);
  if (!ctx) {
    throw new Error("useComposerFocus must be used within ComposerFocusProvider");
  }
  return ctx;
}

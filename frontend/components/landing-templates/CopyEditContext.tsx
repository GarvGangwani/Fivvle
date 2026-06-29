"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { CopyJson } from "@/lib/types";

interface CopyEditContextValue {
  editable: boolean;
  onCopyChange: (copy: CopyJson) => void;
}

const CopyEditContext = createContext<CopyEditContextValue | null>(null);

interface CopyEditProviderProps {
  editable: boolean;
  onCopyChange?: (copy: CopyJson) => void;
  children: ReactNode;
}

export function CopyEditProvider({
  editable,
  onCopyChange,
  children,
}: CopyEditProviderProps) {
  if (!editable || !onCopyChange) {
    return <>{children}</>;
  }

  return (
    <CopyEditContext.Provider value={{ editable: true, onCopyChange }}>
      {children}
    </CopyEditContext.Provider>
  );
}

export function useCopyEdit(): CopyEditContextValue | null {
  return useContext(CopyEditContext);
}

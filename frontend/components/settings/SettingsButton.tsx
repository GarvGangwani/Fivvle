"use client";

import { useState } from "react";
import { Settings } from "lucide-react";
import { SettingsPanel } from "@/components/settings/SettingsPanel";

export function SettingsButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fv-icon-btn"
        aria-label="Open settings"
        title="Settings"
      >
        <Settings className="h-4 w-4" />
      </button>
      <SettingsPanel open={open} onClose={() => setOpen(false)} />
    </>
  );
}

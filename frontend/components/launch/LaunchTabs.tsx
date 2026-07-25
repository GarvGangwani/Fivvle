"use client";

export type LaunchTabId = "copy" | "design" | "share" | "kit";

const TABS: { id: LaunchTabId; label: string }[] = [
  { id: "copy", label: "Copy" },
  { id: "design", label: "Design" },
  { id: "share", label: "Share" },
  { id: "kit", label: "Kit" },
];

type Props = {
  activeTab: LaunchTabId;
  onTabChange: (tab: LaunchTabId) => void;
};

/**
 * Brutalist segmented control for the Launch right rail.
 * Active: yellow fill, black border, 4px offset shadow.
 */
export function LaunchTabs({ activeTab, onTabChange }: Props) {
  return (
    <div
      className="flex shrink-0 gap-1 border-b-2 border-border-master bg-surface-elevated p-2"
      role="tablist"
      aria-label="Launch editor tabs"
    >
      {TABS.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onTabChange(tab.id)}
            className={`flex-1 border-2 border-border-master px-2 py-2 font-label-md text-label-sm uppercase tracking-wider transition-all ${
              active
                ? "bg-brutalist-yellow text-ink-primary shadow-brutal-sm translate-x-0 translate-y-0"
                : "bg-surface-card text-ink-primary hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-brutal-sm"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Pin } from "lucide-react";
import { SAMPLE_PITCH } from "./shared";

interface Note {
  id: string;
  zone: string;
  text: string;
  x: number;
  y: number;
  rot: number;
}

const ZONES = [
  { id: "idea", label: "Core idea", x: 8, y: 12 },
  { id: "audience", label: "Who?", x: 58, y: 8 },
  { id: "pain", label: "Pain", x: 12, y: 52 },
  { id: "edge", label: "Edge", x: 62, y: 48 },
  { id: "risk", label: "Risk", x: 36, y: 72 },
] as const;

const ZONE_PROMPTS: Record<string, string> = {
  audience: "Urban singles tired of swipe apps",
  pain: "Ghosting + superficial matches",
  edge: "Weekly psych match, no photo lottery",
  risk: "Trust without photos upfront",
};

export function EvidenceBoardDemo() {
  const [notes, setNotes] = useState<Note[]>([
    {
      id: "seed",
      zone: "idea",
      text: SAMPLE_PITCH.slice(0, 90) + "…",
      x: 6,
      y: 10,
      rot: -2,
    },
  ]);
  const [highlightZone, setHighlightZone] = useState<string | null>("audience");

  function pinZone(zoneId: string) {
    if (notes.some((n) => n.zone === zoneId)) {
      setHighlightZone(null);
      return;
    }
    const zone = ZONES.find((z) => z.id === zoneId);
    if (!zone) return;
    setNotes((prev) => [
      ...prev,
      {
        id: zoneId,
        zone: zoneId,
        text: ZONE_PROMPTS[zoneId] ?? "Pinned",
        x: zone.x + Math.random() * 4,
        y: zone.y + Math.random() * 4,
        rot: Math.random() * 8 - 4,
      },
    ]);
    const next = ZONES.find((z) => !notes.some((n) => n.zone === z.id) && z.id !== zoneId);
    setHighlightZone(next?.id ?? null);
  }

  const complete = ZONES.every((z) => notes.some((n) => n.zone === z.id));

  return (
    <div className="rd-demo">
      <p className="rd-demo-label">Concept 6</p>
      <h2 className="rd-demo-title">Evidence Board</h2>
      <p className="rd-demo-desc">
        Detective-style cork board. AI highlights empty zones; you pin answers as
        sticky notes.
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
        <div
          className="relative min-h-[340px] overflow-hidden rounded-2xl border border-[var(--fv-border)]"
          style={{
            background:
              "repeating-linear-gradient(45deg, #6b4f3a 0, #6b4f3a 2px, #7a5c45 2px, #7a5c45 8px)",
          }}
        >
          {ZONES.map((zone) => (
            <div
              key={zone.id}
              className={`absolute rounded-lg border-2 border-dashed px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${
                highlightZone === zone.id
                  ? "border-[var(--fv-warning)] bg-[color-mix(in_srgb,var(--fv-warning)_25%,transparent)] text-[var(--fv-warning)]"
                  : "border-white/20 text-white/50"
              }`}
              style={{ left: `${zone.x}%`, top: `${zone.y}%` }}
            >
              {zone.label}
            </div>
          ))}

          {notes.map((note) => (
            <div
              key={note.id}
              className="absolute max-w-[140px] rounded-sm px-2.5 py-2 text-[11px] leading-snug text-slate-800 shadow-md"
              style={{
                left: `${note.x}%`,
                top: `${note.y}%`,
                transform: `rotate(${note.rot}deg)`,
                background: "#fef08a",
              }}
            >
              {note.text}
            </div>
          ))}
        </div>

        <div className="rd-panel">
          {highlightZone ? (
            <>
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-[var(--fv-text)]">
                <Pin className="h-4 w-4 text-[var(--fv-warning)]" />
                Missing: {ZONES.find((z) => z.id === highlightZone)?.label}
              </p>
              <p className="mb-3 text-xs text-[var(--fv-text-muted)]">
                Pin evidence for this zone to strengthen the case.
              </p>
              <button
                type="button"
                className="rd-btn-primary w-full"
                onClick={() => pinZone(highlightZone)}
              >
                Pin answer
              </button>
            </>
          ) : complete ? (
            <p className="text-sm text-[var(--fv-success)]">
              Board complete — hypothesis is documented.
            </p>
          ) : (
            <p className="text-sm text-[var(--fv-text-muted)]">
              Select a zone on the board to continue.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

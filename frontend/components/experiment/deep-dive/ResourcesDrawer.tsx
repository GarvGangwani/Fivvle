"use client";

import { FormEvent, useState } from "react";
import type { ExperimentResource, ResourceType } from "@/lib/types";

type Props = {
  open: boolean;
  resources: ExperimentResource[];
  onClose: () => void;
  onCreate: (payload: {
    title: string;
    url?: string | null;
    note?: string | null;
    resource_type?: ResourceType;
  }) => Promise<void>;
  onDelete: (resourceId: string) => Promise<void>;
};

export function ResourcesDrawer({
  open,
  resources,
  onClose,
  onCreate,
  onDelete,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [resourceType, setResourceType] = useState<ResourceType>("link");
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await onCreate({
        title: title.trim(),
        url: url.trim() || null,
        note: note.trim() || null,
        resource_type: resourceType,
      });
      setTitle("");
      setUrl("");
      setNote("");
      setResourceType("link");
      setExpanded(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside
      className={`fixed bottom-0 right-0 top-0 z-[65] w-96 rounded-l-md border-l-2 border-border-master bg-surface-card shadow-brutal-xl transition-transform ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="flex items-center justify-between border-b-2 border-border-master p-4">
        <h3 className="font-label-md text-label-md uppercase text-ink-primary">
          Resources
        </h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="border-2 border-border-master px-2 py-1 font-label-md text-label-sm uppercase"
          >
            Add new
          </button>
          <button
            type="button"
            onClick={onClose}
            className="font-label-md text-label-sm uppercase text-ink-primary"
          >
            ✕
          </button>
        </div>
      </div>
      {expanded ? (
        <form onSubmit={submit} className="space-y-2 border-b-2 border-border-master p-4">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="w-full border-2 border-border-master bg-surface-elevated p-2"
            required
          />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://..."
            className="w-full border-2 border-border-master bg-surface-elevated p-2"
          />
          <select
            value={resourceType}
            onChange={(e) => setResourceType(e.target.value as ResourceType)}
            className="w-full border-2 border-border-master bg-surface-elevated p-2"
          >
            <option value="link">link</option>
            <option value="doc">doc</option>
            <option value="image">image</option>
            <option value="competitor">competitor</option>
            <option value="other">other</option>
          </select>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note"
            className="w-full border-2 border-border-master bg-surface-elevated p-2"
            rows={3}
          />
          <button
            type="submit"
            disabled={saving}
            className="border-2 border-border-master bg-brand-primary px-3 py-2 font-label-md text-label-sm uppercase text-ink-inverse"
          >
            Save
          </button>
        </form>
      ) : null}
      <div className="h-[calc(100%-72px)] space-y-2 overflow-y-auto p-4">
        {resources.length === 0 ? (
          <p className="font-body-sm text-body-sm text-ink-tertiary">
            No resources yet. Add your first link, document, or competitor above.
          </p>
        ) : (
          resources.map((r) => (
            <article key={r.id} className="border-2 border-border-master p-3">
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-headline text-headline-sm text-ink-primary">
                  {r.title}
                </h4>
                <button
                  type="button"
                  onClick={() => void onDelete(r.id)}
                  className="font-label-md text-label-sm uppercase text-ink-tertiary"
                >
                  Delete
                </button>
              </div>
              <p className="mt-1 font-mono text-mono-sm uppercase text-ink-tertiary">
                {r.resource_type}
              </p>
              {r.url ? (
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 block break-all font-body-sm text-body-sm text-brand-primary"
                >
                  {r.url}
                </a>
              ) : null}
              {r.note ? (
                <p className="mt-1 line-clamp-2 font-body-sm text-body-sm text-ink-secondary">
                  {r.note}
                </p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </aside>
  );
}

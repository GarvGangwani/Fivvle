"use client";

export type RefineMessageAttachment = {
  id: string;
  filename: string;
  content_kind?: string;
  previewUrl?: string | null;
};

type Props = {
  attachments: RefineMessageAttachment[];
};

function isImageKind(attachment: RefineMessageAttachment): boolean {
  if (attachment.content_kind?.startsWith("image")) return true;
  if (attachment.previewUrl) return true;
  return /\.(png|jpe?g|webp)$/i.test(attachment.filename);
}

export function MessageAttachments({ attachments }: Props) {
  if (attachments.length === 0) return null;

  return (
    <ul className="mt-3 flex flex-wrap gap-2">
      {attachments.map((attachment) => (
        <li
          key={attachment.id}
          className="rounded-sm border-2 border-border-master bg-surface-card h-14 flex items-center gap-2 px-2 max-w-full"
        >
          {isImageKind(attachment) && attachment.previewUrl ? (
            <div className="w-12 h-12 rounded-sm border-2 border-border-master overflow-hidden shrink-0 bg-surface-elevated">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={attachment.previewUrl}
                alt={attachment.filename}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <div className="w-12 h-12 rounded-sm border-2 border-border-master bg-surface-elevated flex items-center justify-center shrink-0">
              <span
                className="material-symbols-outlined text-ink-secondary"
                style={{ fontSize: 22 }}
                aria-hidden="true"
              >
                {isImageKind(attachment) ? "image" : "description"}
              </span>
            </div>
          )}
          <span className="font-mono text-mono-sm text-ink-secondary truncate max-w-[140px]">
            {attachment.filename}
          </span>
        </li>
      ))}
    </ul>
  );
}

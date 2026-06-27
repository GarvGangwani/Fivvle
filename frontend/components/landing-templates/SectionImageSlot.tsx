"use client";

import {
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { Loader2, Plus, X } from "lucide-react";
import { ApiError, uploadSectionImage } from "@/lib/api";
import styles from "./section-image-slot.module.css";

const ACCEPTED_TYPES = "image/png,image/jpeg,image/webp";
const MAX_SECTION_IMAGE_MB = 5;

interface SectionImageSlotProps {
  slotId: string;
  imageUrl?: string;
  className?: string;
  placeholderClassName?: string;
  style?: CSSProperties;
  placeholderStyle?: CSSProperties;
  placeholderChildren?: ReactNode;
  fill?: boolean;
  alt?: string;
  editable?: boolean;
  experimentId?: string;
  onImageChange?: (slotId: string, url: string | null) => void;
}

export function SectionImageSlot({
  slotId,
  imageUrl,
  className,
  placeholderClassName,
  style,
  placeholderStyle,
  placeholderChildren,
  fill = false,
  alt = "",
  editable = false,
  experimentId,
  onImageChange,
}: SectionImageSlotProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const hasImage = Boolean(imageUrl?.trim());
  const canEdit = editable && Boolean(experimentId) && Boolean(onImageChange);

  const handleFileSelect = async (file: File | null) => {
    if (!file || !experimentId || !onImageChange) return;
    setUploadError(null);

    if (!file.type.match(/^image\/(png|jpeg|webp)$/)) {
      setUploadError("Use PNG, JPEG, or WebP.");
      return;
    }
    if (file.size > MAX_SECTION_IMAGE_MB * 1024 * 1024) {
      setUploadError(`Max ${MAX_SECTION_IMAGE_MB} MB.`);
      return;
    }

    setUploading(true);
    try {
      const { image_url } = await uploadSectionImage(experimentId, file);
      onImageChange(slotId, image_url);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body;
        const detail =
          body &&
          typeof body === "object" &&
          "detail" in body &&
          typeof (body as { detail?: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : null;
        setUploadError(detail ?? `Upload failed (${err.status}).`);
      } else {
        setUploadError(err instanceof Error ? err.message : "Upload failed.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleRemove = () => {
    setUploadError(null);
    onImageChange?.(slotId, null);
  };

  return (
    <div
      className={`${styles.root} ${fill ? styles.fill : ""} ${className ?? ""}`.trim()}
      style={style}
      data-section-image-slot={slotId}
    >
      {hasImage ? (
        <img src={imageUrl} alt={alt} className={styles.image} />
      ) : (
        <div
          className={`${styles.placeholder} ${placeholderClassName ?? ""}`.trim()}
          style={placeholderStyle}
          aria-hidden
        >
          {placeholderChildren}
        </div>
      )}

      {canEdit && (
        <div className={styles.controls}>
          {!hasImage ? (
            <button
              type="button"
              className={styles.addBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              aria-label="Upload image"
              title="Upload image"
            >
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-5 w-5" strokeWidth={2.25} />
              )}
            </button>
          ) : (
            <button
              type="button"
              className={styles.removeBtn}
              onClick={handleRemove}
              aria-label="Remove image"
              title="Remove image"
            >
              <X className="h-3.5 w-3.5" strokeWidth={2.25} />
              Remove
            </button>
          )}
          {uploadError ? <span className={styles.error}>{uploadError}</span> : null}
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            className="sr-only"
            tabIndex={-1}
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              void handleFileSelect(file);
            }}
          />
        </div>
      )}
    </div>
  );
}

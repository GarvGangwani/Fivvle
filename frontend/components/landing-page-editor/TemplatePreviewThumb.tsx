"use client";

import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CopyJson, PageJson } from "@/lib/types";
import type { TemplateId } from "@/lib/templates";
import { PAGE_TEMPLATES } from "@/lib/templates";
import { buildPageForTemplatePreview } from "@/lib/template-preview-page";
import { TemplateRenderer } from "@/components/landing-templates/TemplateRenderer";

const PREVIEW_WIDTH = 1280;

interface TemplatePreviewThumbProps {
  templateId: TemplateId;
  copy: CopyJson;
  page: PageJson;
  projectName: string;
}

export function TemplatePreviewThumb({
  templateId,
  copy,
  page,
  projectName,
}: TemplatePreviewThumbProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.2);
  const [mounted, setMounted] = useState(false);

  const previewPage = useMemo(
    () => buildPageForTemplatePreview(page, copy, templateId),
    [page, copy, templateId],
  );

  const fallback = PAGE_TEMPLATES.find((t) => t.id === templateId)?.preview;

  useLayoutEffect(() => {
    const el = hostRef.current;
    if (!el) return;

    const updateScale = () => {
      const width = el.clientWidth;
      if (width > 0) setScale(width / PREVIEW_WIDTH);
    };

    updateScale();
    const ro = new ResizeObserver(updateScale);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setMounted(true);
          io.disconnect();
        }
      },
      { rootMargin: "120px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={hostRef}
      className="lp-template-swatch lp-template-preview"
      data-theme="light"
      aria-hidden
    >
      {!mounted && fallback ? (
        <div
          className="lp-template-preview-fallback"
          style={{ background: fallback.bg }}
        >
          <div
            className="h-full w-full"
            style={{
              background: `linear-gradient(135deg, ${fallback.accent}55, transparent 70%)`,
            }}
          />
        </div>
      ) : (
        <div
          className="lp-template-preview-inner"
          style={{
            width: PREVIEW_WIDTH,
            transform: `scale(${scale})`,
          }}
        >
          <TemplateRenderer
            copy={copy}
            page={previewPage}
            projectName={projectName}
            templateId={templateId}
            forEditor={false}
          />
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { TemplateRenderer } from "@/components/landing-templates/TemplateRenderer";
import {
  DEVICE_PREVIEW_MESSAGE,
  isDevicePreviewPayload,
  type DevicePreviewPayload,
} from "@/lib/device-preview-messages";

function notifyParentLoaded() {
  window.parent.postMessage(
    { type: DEVICE_PREVIEW_MESSAGE.LOADED },
    window.location.origin,
  );
}

export default function DevicePreviewFramePage() {
  const [payload, setPayload] = useState<DevicePreviewPayload | null>(null);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== DEVICE_PREVIEW_MESSAGE.UPDATE) return;
      if (!isDevicePreviewPayload(event.data.payload)) return;
      setPayload(event.data.payload);
    }

    const prevBody = document.body.style.cssText;
    const prevHtml = document.documentElement.style.cssText;
    document.body.style.margin = "0";
    document.body.style.overflowX = "hidden";
    document.body.style.overflowY = "auto";
    document.documentElement.style.height = "auto";

    window.addEventListener("message", onMessage);
    window.parent.postMessage({ type: DEVICE_PREVIEW_MESSAGE.READY }, window.location.origin);

    return () => {
      window.removeEventListener("message", onMessage);
      document.body.style.cssText = prevBody;
      document.documentElement.style.cssText = prevHtml;
    };
  }, []);

  useEffect(() => {
    if (!payload) return;
    let cancelled = false;
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        if (!cancelled) notifyParentLoaded();
      });
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [payload]);

  if (!payload) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "var(--fv-bg, #080c14)",
        }}
      />
    );
  }

  return (
    <div data-fivvle-public-landing>
      <TemplateRenderer
        copy={payload.copy}
        page={payload.page}
        projectName={payload.projectName}
        templateId={payload.templateId}
        forEditor={payload.forEditor === true}
        isPublished={payload.isPublished === true}
        publicationSlug={payload.publicationSlug}
        ctaConfig={payload.ctaConfig}
      />
    </div>
  );
}

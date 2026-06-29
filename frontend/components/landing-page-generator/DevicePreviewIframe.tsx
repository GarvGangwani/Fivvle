"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  DEVICE_PREVIEW_MESSAGE,
  type DevicePreviewPayload,
} from "@/lib/device-preview-messages";
import styles from "./device-preview.module.css";

interface DevicePreviewIframeProps {
  width: number;
  height: number;
  payload: DevicePreviewPayload;
  loadKey: string;
}

function PreviewLoadingOverlay() {
  return (
    <div className={styles.previewLoadingOverlay} role="status" aria-live="polite">
      <div className={styles.previewLoadingOverlayContent}>
        <Loader2 className={styles.previewLoadingSpinner} aria-hidden />
        <span>Loading…</span>
      </div>
    </div>
  );
}

export function DevicePreviewIframe({
  width,
  height,
  payload,
  loadKey,
}: DevicePreviewIframeProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === DEVICE_PREVIEW_MESSAGE.READY) {
        setReady(true);
      }
      if (event.data?.type === DEVICE_PREVIEW_MESSAGE.LOADED) {
        setLoading(false);
      }
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    setLoading(true);
  }, [loadKey]);

  useEffect(() => {
    if (!ready) return;
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    win.postMessage(
      { type: DEVICE_PREVIEW_MESSAGE.UPDATE, payload },
      window.location.origin,
    );
  }, [ready, payload, loadKey]);

  return (
    <div className={styles.previewScreenWrap} style={{ width, height }}>
      <iframe
        ref={iframeRef}
        title="Device preview"
        src="/preview/device"
        width={width}
        height={height}
        className="block border-0 bg-[var(--bg,#fff)]"
        style={{ width, height, colorScheme: "normal" }}
      />
      {loading ? <PreviewLoadingOverlay /> : null}
    </div>
  );
}

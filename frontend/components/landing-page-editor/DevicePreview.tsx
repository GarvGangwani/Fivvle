"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Maximize2, Loader2, X } from "lucide-react";
import {
  DEVICE_CATEGORIES,
  frameChromeSize,
  getDeviceById,
  getDevicesByCategory,
  resolveViewport,
  type DeviceCategory,
  type DeviceFrame,
  type DevicePreset,
} from "@/lib/device-presets";
import styles from "./device-preview.module.css";
import { DevicePreviewIframe } from "./DevicePreviewIframe";
import type { DevicePreviewPayload } from "@/lib/device-preview-messages";
import {
  PreviewSaveStatusBadge,
  type PreviewSaveStatus,
} from "./PreviewSaveStatus";

interface DevicePreviewProps {
  children?: ReactNode;
  /** When set, phone/tablet previews render in an isolated iframe for accurate vw/media queries. */
  previewPayload?: DevicePreviewPayload;
  /** When true, preview fills available width with no device chrome. */
  defaultDeviceId?: string;
  /** Simplified Desktop / Tablet / Mobile toolbar for the editor. */
  variant?: "full" | "editor";
  /** Use fluid full-width preview (mobile editor preview tab). */
  mobileFluid?: boolean;
  /** Hint that inline copy/image editing works in desktop preview only. */
  showInlineEditDisclaimer?: boolean;
  /** Autosave state shown in the editor preview toolbar. */
  saveStatus?: PreviewSaveStatus;
  saveErrorDetail?: string | null;
}

const EDITOR_DEVICES = [
  { id: "desktop-1440", label: "Desktop" },
  { id: "ipad-air", label: "Tablet" },
  { id: "iphone-15-pro", label: "Mobile" },
] as const;

function previewLoadKey(
  deviceId: string,
  payload: DevicePreviewPayload | undefined,
): string {
  if (!payload) return deviceId;
  const generationId = payload.page?.meta?.generation_id ?? "local";
  return `${deviceId}:${payload.templateId}:${generationId}`;
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

function InlinePreviewShell({
  loadKey,
  children,
}: {
  loadKey: string;
  children: ReactNode;
}) {
  const [loading, setLoading] = useState(true);

  useLayoutEffect(() => {
    setLoading(true);
    let cancelled = false;
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        if (!cancelled) setLoading(false);
      });
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [loadKey]);

  return (
    <div className={styles.previewScreenWrap}>
      {children}
      {loading ? <PreviewLoadingOverlay /> : null}
    </div>
  );
}

function DeviceFrameShell({
  frame,
  viewportWidth,
  viewportHeight,
  children,
}: {
  frame: DeviceFrame;
  viewportWidth: number;
  viewportHeight: number;
  children: ReactNode;
}) {
  const screenStyle = {
    width: viewportWidth,
    height: viewportHeight,
  };

  if (frame === "laptop") {
    return (
      <div className={styles.frameLaptop}>
        <div className={styles.laptopCamera} aria-hidden />
        <div className={styles.laptopScreen} style={screenStyle}>
          <div className={styles.screenScroll}>{children}</div>
        </div>
        <div className={styles.laptopBase} aria-hidden />
      </div>
    );
  }

  if (frame === "tablet") {
    return (
      <div className={styles.frameTablet}>
        <div className={styles.tabletScreen} style={screenStyle}>
          <div className={styles.screenScroll}>{children}</div>
        </div>
      </div>
    );
  }

  if (frame === "phone" || frame === "phone-notch") {
    const frameClass =
      frame === "phone-notch" ? styles.framePhoneNotch : styles.framePhone;
    return (
      <div className={frameClass}>
        <div className={styles.phoneScreen} style={screenStyle}>
          {frame === "phone-notch" && (
            <div className={styles.dynamicIsland} aria-hidden />
          )}
          <div className={styles.screenScroll}>{children}</div>
          <div className={styles.homeIndicator} aria-hidden />
        </div>
      </div>
    );
  }

  if (frame === "foldable") {
    return (
      <div className={styles.frameFoldable}>
        <div className={styles.foldScreen} style={screenStyle}>
          <div className={styles.screenScroll}>{children}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.frameNone} style={screenStyle}>
      <div className={styles.screenScroll}>{children}</div>
    </div>
  );
}

function PreviewToolbar({
  category,
  onCategoryChange,
  deviceId,
  onDeviceChange,
  landscape,
  onRotate,
  canRotate,
  sizeLabel,
  isFullscreen,
  onToggleFullscreen,
  isFluid,
}: {
  category: DeviceCategory;
  onCategoryChange: (c: DeviceCategory) => void;
  deviceId: string;
  onDeviceChange: (id: string) => void;
  landscape: boolean;
  onRotate: () => void;
  canRotate: boolean;
  sizeLabel: string;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  isFluid: boolean;
}) {
  const devices = getDevicesByCategory(category);

  return (
    <div className={styles.toolbar}>
      <div className={styles.categoryTabs}>
        {DEVICE_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            type="button"
            className={`${styles.categoryTab} ${
              category === cat.id ? styles.categoryTabActive : ""
            }`}
            onClick={() => onCategoryChange(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <select
        className={styles.deviceSelect}
        value={deviceId}
        onChange={(e) => onDeviceChange(e.target.value)}
        aria-label="Device model"
      >
        {devices.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </select>

      {!isFluid && (
        <span className={styles.sizeLabel}>{sizeLabel}</span>
      )}

      <div className={styles.toolbarActions}>
        {canRotate && (
          <button
            type="button"
            className={`${styles.iconBtn} ${landscape ? styles.iconBtnActive : ""}`}
            onClick={onRotate}
            title={landscape ? "Portrait" : "Landscape"}
            aria-label="Rotate device"
          >
            ↻
          </button>
        )}
        <button
          type="button"
          className={`${styles.iconBtn} ${isFullscreen ? styles.iconBtnActive : ""}`}
          onClick={onToggleFullscreen}
          title={isFullscreen ? "Exit full screen" : "Full screen preview"}
          aria-label={isFullscreen ? "Exit full screen" : "Full screen preview"}
        >
          {isFullscreen ? (
            <X className="h-4 w-4" />
          ) : (
            <Maximize2 className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

function ScaledPreview({
  device,
  landscape,
  isFullscreen,
  previewPayload,
  children,
}: {
  device: DevicePreset;
  landscape: boolean;
  isFullscreen: boolean;
  previewPayload?: DevicePreviewPayload;
  children?: ReactNode;
}) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const { width, height } = resolveViewport(device, landscape);
  const chrome = frameChromeSize(device.frame);
  const totalW = (width ?? 0) + chrome.padX * 2;
  const totalH = (height ?? 0) + chrome.padTop + chrome.padBottom;

  const useIsolatedViewport =
    previewPayload != null &&
    width != null &&
    height != null &&
    (device.category === "phone" ||
      device.category === "tablet" ||
      device.category === "foldable");

  const loadKey = previewLoadKey(device.id, previewPayload);

  const screenContent =
    useIsolatedViewport && width != null && height != null ? (
      <DevicePreviewIframe
        width={width}
        height={height}
        payload={previewPayload}
        loadKey={loadKey}
      />
    ) : (
      <InlinePreviewShell loadKey={loadKey}>{children}</InlinePreviewShell>
    );

  const updateScale = useCallback(() => {
    const area = areaRef.current;
    if (!area || width == null || height == null) {
      setScale(1);
      return;
    }
    const pad = isFullscreen ? 48 : 24;
    const availW = Math.max(0, area.clientWidth - pad);
    const availH = Math.max(0, area.clientHeight - pad);
    const next = Math.min(1, availW / totalW, availH / totalH);
    setScale(Math.max(0.15, next));
  }, [width, height, totalW, totalH, isFullscreen]);

  useLayoutEffect(() => {
    updateScale();
  }, [updateScale, device.id, landscape, isFullscreen]);

  useEffect(() => {
    const area = areaRef.current;
    if (!area) return;
    const ro = new ResizeObserver(() => updateScale());
    ro.observe(area);
    return () => ro.disconnect();
  }, [updateScale]);

  if (width == null || height == null) {
    return (
      <div
        ref={areaRef}
        className={`${styles.viewportArea} ${styles.viewportAreaFluid}`}
      >
        <div className={styles.fluidWrap}>{screenContent ?? children}</div>
      </div>
    );
  }

  return (
    <div ref={areaRef} className={styles.viewportArea}>
      <div
        className={styles.scaledClip}
        style={{ width: totalW * scale, height: totalH * scale }}
      >
        <div
          className={styles.scaledInner}
          style={{
            width: totalW,
            height: totalH,
            transform: `scale(${scale})`,
            ["--preview-inverse-scale" as string]: String(
              scale > 0 ? Math.min(3.5, 1 / scale) : 1,
            ),
          }}
        >
          <DeviceFrameShell
            frame={device.frame}
            viewportWidth={width}
            viewportHeight={height}
          >
            {screenContent}
          </DeviceFrameShell>
        </div>
      </div>
    </div>
  );
}

export function DevicePreview({
  children,
  previewPayload,
  defaultDeviceId = "fluid",
  variant = "full",
  mobileFluid = false,
  showInlineEditDisclaimer = false,
  saveStatus = "idle",
  saveErrorDetail = null,
}: DevicePreviewProps) {
  const isEditor = variant === "editor";
  const initialId = mobileFluid ? "fluid" : isEditor ? "desktop-1440" : defaultDeviceId;
  const initial = getDeviceById(initialId);
  const [category, setCategory] = useState<DeviceCategory>(initial.category);
  const [deviceId, setDeviceId] = useState(initial.id);
  const [landscape, setLandscape] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (!mobileFluid) return;

    const mq = window.matchMedia("(max-width: 1023px)");
    const syncDevice = () => {
      if (mq.matches) {
        setDeviceId("fluid");
        setLandscape(false);
        setCategory(getDeviceById("fluid").category);
      } else if (isEditor) {
        setDeviceId("desktop-1440");
        setLandscape(false);
        setCategory(getDeviceById("desktop-1440").category);
      }
    };

    syncDevice();
    mq.addEventListener("change", syncDevice);
    return () => mq.removeEventListener("change", syncDevice);
  }, [mobileFluid, isEditor]);

  const device = getDeviceById(deviceId);
  const { width, height } = resolveViewport(device, landscape);
  const isFluid = width == null;

  const handleCategoryChange = (next: DeviceCategory) => {
    setCategory(next);
    const first = getDevicesByCategory(next)[0];
    if (first) {
      setDeviceId(first.id);
      setLandscape(false);
    }
  };

  const handleDeviceChange = (id: string) => {
    setDeviceId(id);
    setLandscape(false);
    const d = getDeviceById(id);
    setCategory(d.category);
    if (id === "desktop-full") {
      setIsFullscreen(true);
    }
  };

  const sizeLabel =
    width != null && height != null
      ? `${width} × ${height}${landscape ? " ↻" : ""}`
      : "Responsive";

  const isDesktopEditorPreview =
    deviceId === "desktop-1440" || deviceId === "desktop-full";

  useEffect(() => {
    if (!isFullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [isFullscreen]);

  const editorToolbar = isEditor && !isFullscreen && !mobileFluid ? (
    <div className={styles.editorToolbar}>
      <div className={styles.editorToolbarStart}>
        {showInlineEditDisclaimer && !isDesktopEditorPreview ? (
          <p className={styles.editDisclaimer}>
            Direct editing is only available in the desktop preview
          </p>
        ) : null}
      </div>
      <div className={styles.editorToolbarCenter}>
        <div className={styles.editorDeviceSwitcher}>
          {EDITOR_DEVICES.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleDeviceChange(preset.id)}
              className={`fv-tab-pill ${
                deviceId === preset.id ? "fv-tab-pill-active" : ""
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.editorToolbarEnd}>
        <PreviewSaveStatusBadge status={saveStatus} errorDetail={saveErrorDetail} />
        <button
          type="button"
          className={styles.iconBtn}
          onClick={() => setIsFullscreen(true)}
          title="Full screen preview"
          aria-label="Full screen preview"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  ) : null;

  const toolbar = isEditor ? null : (
    <PreviewToolbar
      category={category}
      onCategoryChange={handleCategoryChange}
      deviceId={deviceId}
      onDeviceChange={handleDeviceChange}
      landscape={landscape}
      onRotate={() => setLandscape((v) => !v)}
      canRotate={device.rotatable}
      sizeLabel={sizeLabel}
      isFullscreen={isFullscreen}
      onToggleFullscreen={() => setIsFullscreen((v) => !v)}
      isFluid={isFluid}
    />
  );

  const preview = (
    <ScaledPreview
      device={device}
      landscape={landscape}
      isFullscreen={isFullscreen}
      previewPayload={previewPayload}
    >
      {children}
    </ScaledPreview>
  );

  if (isFullscreen && isEditor) {
    return (
      <div className="fixed inset-0 z-[200] flex flex-col bg-[var(--fv-bg)]">
        <button
          type="button"
          onClick={() => setIsFullscreen(false)}
          className="fv-btn-ghost fixed top-4 right-4 z-[201] inline-flex items-center gap-2 px-3 py-2"
          aria-label="Exit full screen"
        >
          <X className="h-4 w-4" />
        </button>
        <div className="flex h-full min-h-0 flex-1 flex-col pt-14">
          <ScaledPreview
            device={device}
            landscape={landscape}
            isFullscreen
            previewPayload={previewPayload}
          >
            {children}
          </ScaledPreview>
        </div>
      </div>
    );
  }

  if (isFullscreen && !isEditor) {
    return (
      <div className={`${styles.stage} ${styles.stageFullscreen}`}>
        {toolbar}
        {preview}
      </div>
    );
  }

  return (
    <div className={styles.stage}>
      {mobileFluid && saveStatus !== "idle" ? (
        <div className={styles.mobileSaveBar}>
          <PreviewSaveStatusBadge status={saveStatus} errorDetail={saveErrorDetail} />
        </div>
      ) : null}
      {editorToolbar}
      {toolbar}
      {preview}
    </div>
  );
}

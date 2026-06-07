"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
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

interface DevicePreviewProps {
  children: ReactNode;
  /** When true, preview fills available width with no device chrome. */
  defaultDeviceId?: string;
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
          {isFullscreen ? "✕" : "⛶"}
        </button>
      </div>
    </div>
  );
}

function ScaledPreview({
  device,
  landscape,
  isFullscreen,
  children,
}: {
  device: DevicePreset;
  landscape: boolean;
  isFullscreen: boolean;
  children: ReactNode;
}) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const { width, height } = resolveViewport(device, landscape);
  const chrome = frameChromeSize(device.frame);
  const totalW = (width ?? 0) + chrome.padX * 2;
  const totalH = (height ?? 0) + chrome.padTop + chrome.padBottom;

  const updateScale = useCallback(() => {
    const area = areaRef.current;
    if (!area || width == null || height == null) {
      setScale(1);
      return;
    }
    const pad = isFullscreen ? 48 : 32;
    const availW = area.clientWidth - pad;
    const availH = area.clientHeight - pad;
    const next = Math.min(1, availW / totalW, availH / totalH);
    setScale(Math.max(0.2, next));
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
        <div className={styles.fluidWrap}>{children}</div>
      </div>
    );
  }

  return (
    <div ref={areaRef} className={styles.viewportArea}>
      <div
        className={styles.scaledWrap}
        style={{ width: totalW * scale, height: totalH * scale }}
      >
        <div
          className={styles.scaledInner}
          style={{
            width: totalW,
            height: totalH,
            transform: `scale(${scale})`,
          }}
        >
          <DeviceFrameShell
            frame={device.frame}
            viewportWidth={width}
            viewportHeight={height}
          >
            {children}
          </DeviceFrameShell>
        </div>
      </div>
    </div>
  );
}

export function DevicePreview({
  children,
  defaultDeviceId = "fluid",
}: DevicePreviewProps) {
  const initial = getDeviceById(defaultDeviceId);
  const [category, setCategory] = useState<DeviceCategory>(initial.category);
  const [deviceId, setDeviceId] = useState(initial.id);
  const [landscape, setLandscape] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  const toolbar = (
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
    >
      {children}
    </ScaledPreview>
  );

  if (isFullscreen) {
    return (
      <div className={`${styles.stage} ${styles.stageFullscreen}`}>
        {toolbar}
        {preview}
      </div>
    );
  }

  return (
    <div className={styles.stage}>
      {toolbar}
      {preview}
    </div>
  );
}

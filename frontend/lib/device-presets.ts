export type DeviceCategory = "responsive" | "laptop" | "tablet" | "phone" | "foldable";

export type DeviceFrame = "none" | "laptop" | "tablet" | "phone" | "phone-notch" | "foldable";

export interface DevicePreset {
  id: string;
  name: string;
  category: DeviceCategory;
  /** Viewport width in CSS pixels. `null` = fluid (fills container). */
  width: number | null;
  /** Viewport height in CSS pixels. `null` = fluid height. */
  height: number | null;
  frame: DeviceFrame;
  /** Show rotate control (portrait ↔ landscape). */
  rotatable: boolean;
}

export const DEVICE_CATEGORIES: { id: DeviceCategory; label: string }[] = [
  { id: "responsive", label: "Desktop" },
  { id: "laptop", label: "Laptop" },
  { id: "tablet", label: "Tablet" },
  { id: "phone", label: "Phone" },
  { id: "foldable", label: "Foldable" },
];

/** Logical viewport sizes commonly used in design/dev tools. */
export const DEVICE_PRESETS: DevicePreset[] = [
  {
    id: "fluid",
    name: "Responsive",
    category: "responsive",
    width: null,
    height: null,
    frame: "none",
    rotatable: false,
  },
  {
    id: "desktop-full",
    name: "Full screen",
    category: "responsive",
    width: null,
    height: null,
    frame: "none",
    rotatable: false,
  },
  {
    id: "desktop-1920",
    name: "Desktop HD",
    category: "responsive",
    width: 1920,
    height: 1080,
    frame: "none",
    rotatable: false,
  },
  {
    id: "desktop-1440",
    name: "Desktop",
    category: "responsive",
    width: 1440,
    height: 900,
    frame: "none",
    rotatable: false,
  },
  {
    id: "macbook-pro-16",
    name: 'MacBook Pro 16"',
    category: "laptop",
    width: 1728,
    height: 1117,
    frame: "laptop",
    rotatable: false,
  },
  {
    id: "macbook-air-13",
    name: 'MacBook Air 13"',
    category: "laptop",
    width: 1280,
    height: 832,
    frame: "laptop",
    rotatable: false,
  },
  {
    id: "macbook-pro-14",
    name: 'MacBook Pro 14"',
    category: "laptop",
    width: 1512,
    height: 982,
    frame: "laptop",
    rotatable: false,
  },
  {
    id: "ipad-pro-12",
    name: 'iPad Pro 12.9"',
    category: "tablet",
    width: 1024,
    height: 1366,
    frame: "tablet",
    rotatable: true,
  },
  {
    id: "ipad-air",
    name: "iPad Air",
    category: "tablet",
    width: 820,
    height: 1180,
    frame: "tablet",
    rotatable: true,
  },
  {
    id: "ipad-mini",
    name: "iPad Mini",
    category: "tablet",
    width: 768,
    height: 1024,
    frame: "tablet",
    rotatable: true,
  },
  {
    id: "iphone-15-pro",
    name: "iPhone 15 Pro",
    category: "phone",
    width: 393,
    height: 852,
    frame: "phone-notch",
    rotatable: true,
  },
  {
    id: "iphone-15-pro-max",
    name: "iPhone 15 Pro Max",
    category: "phone",
    width: 430,
    height: 932,
    frame: "phone-notch",
    rotatable: true,
  },
  {
    id: "iphone-14",
    name: "iPhone 14",
    category: "phone",
    width: 390,
    height: 844,
    frame: "phone-notch",
    rotatable: true,
  },
  {
    id: "iphone-se",
    name: "iPhone SE",
    category: "phone",
    width: 375,
    height: 667,
    frame: "phone",
    rotatable: true,
  },
  {
    id: "pixel-8",
    name: "Pixel 8",
    category: "phone",
    width: 412,
    height: 915,
    frame: "phone",
    rotatable: true,
  },
  {
    id: "galaxy-s24",
    name: "Galaxy S24",
    category: "phone",
    width: 360,
    height: 780,
    frame: "phone",
    rotatable: true,
  },
  {
    id: "galaxy-z-fold-cover",
    name: "Galaxy Z Fold (cover)",
    category: "foldable",
    width: 344,
    height: 882,
    frame: "phone",
    rotatable: true,
  },
  {
    id: "galaxy-z-fold-inner",
    name: "Galaxy Z Fold (unfolded)",
    category: "foldable",
    width: 768,
    height: 1076,
    frame: "foldable",
    rotatable: true,
  },
  {
    id: "surface-duo",
    name: "Surface Duo",
    category: "foldable",
    width: 540,
    height: 720,
    frame: "foldable",
    rotatable: true,
  },
];

export function getDeviceById(id: string): DevicePreset {
  return DEVICE_PRESETS.find((d) => d.id === id) ?? DEVICE_PRESETS[0];
}

export function getDevicesByCategory(category: DeviceCategory): DevicePreset[] {
  return DEVICE_PRESETS.filter((d) => d.category === category);
}

export function resolveViewport(
  device: DevicePreset,
  landscape: boolean,
): { width: number | null; height: number | null } {
  if (device.width == null || device.height == null) {
    return { width: null, height: null };
  }
  if (!landscape || !device.rotatable) {
    return { width: device.width, height: device.height };
  }
  return { width: device.height, height: device.width };
}

/** Extra chrome around the viewport (bezel + base). */
export function frameChromeSize(frame: DeviceFrame): { padX: number; padTop: number; padBottom: number } {
  switch (frame) {
    case "laptop":
      return { padX: 24, padTop: 24, padBottom: 28 };
    case "tablet":
      return { padX: 20, padTop: 20, padBottom: 20 };
    case "phone":
    case "phone-notch":
      return { padX: 14, padTop: 14, padBottom: 14 };
    case "foldable":
      return { padX: 18, padTop: 18, padBottom: 18 };
    default:
      return { padX: 0, padTop: 0, padBottom: 0 };
  }
}

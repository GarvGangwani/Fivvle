import type { RazorpayConstructor } from "@/types/razorpay";

const SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

let scriptPromise: Promise<RazorpayConstructor> | null = null;

export function loadRazorpayCheckout(): Promise<RazorpayConstructor> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Razorpay Checkout is browser-only"));
  }
  if (window.Razorpay) {
    return Promise.resolve(window.Razorpay);
  }
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(
        `script[src="${SCRIPT_SRC}"]`,
      );
      if (existing) {
        existing.addEventListener("load", () => {
          if (window.Razorpay) resolve(window.Razorpay);
          else reject(new Error("Razorpay failed to load"));
        });
        existing.addEventListener("error", () => {
          reject(new Error("Razorpay failed to load"));
        });
        return;
      }
      const script = document.createElement("script");
      script.src = SCRIPT_SRC;
      script.async = true;
      script.onload = () => {
        if (window.Razorpay) resolve(window.Razorpay);
        else reject(new Error("Razorpay failed to load"));
      };
      script.onerror = () => reject(new Error("Razorpay failed to load"));
      document.body.appendChild(script);
    });
  }
  return scriptPromise;
}

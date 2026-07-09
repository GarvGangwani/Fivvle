"use client";

import { useCallback, useEffect, useState } from "react";
import { FiveActsSection } from "./FiveActsSection";
import { HeroSection } from "./HeroSection";
import { MarketingFooter } from "./MarketingFooter";
import { MarketingNav } from "./MarketingNav";
import { MobileComposerPill } from "./MobileComposerPill";
import { PricingSection } from "./PricingSection";
import { TestimonialsSection } from "./TestimonialsSection";

export function MarketingLandingPage() {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showComingSoon = useCallback(() => {
    setToastMessage("Coming soon");
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  return (
    <div className="min-h-screen bg-canvas-bg text-ink-primary">
      <MarketingNav />
      <main>
        <HeroSection onDemoClick={showComingSoon} />
        <FiveActsSection />
        <TestimonialsSection />
        <PricingSection />
      </main>
      <MarketingFooter onDemoClick={showComingSoon} />
      <MobileComposerPill />

      {toastMessage ? (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-24 left-1/2 z-[60] -translate-x-1/2 border-2 border-border-master bg-surface-card px-4 py-3 font-body-md text-body-md text-ink-primary shadow-brutal-md md:bottom-8"
        >
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}

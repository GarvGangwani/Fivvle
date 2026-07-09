import type { Metadata } from "next";
import { ComingSoonPage } from "@/components/marketing/ComingSoonPage";

export const metadata: Metadata = {
  title: "Demo — Fivvle",
  description:
    "Watch a full Fivvle validation run-through from Spark to Signal — demo coming soon.",
  robots: { index: false, follow: true },
};

export default function DemoPage() {
  return (
    <ComingSoonPage
      eyebrow="PRODUCT DEMO"
      headline="Watch Fivvle validate an idea in real time."
      body="A recorded run-through of a full validation — from Spark to Signal — is coming soon. In the meantime, start your own."
      ctaLabel="START A VALIDATION →"
      ctaHref="/login?intent=start"
    />
  );
}

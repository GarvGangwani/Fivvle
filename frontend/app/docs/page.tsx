import type { Metadata } from "next";
import { ComingSoonPage } from "@/components/marketing/ComingSoonPage";

export const metadata: Metadata = {
  title: "Documentation — Fivvle",
  description:
    "How Fivvle works: pipeline, pricing, product decisions.",
  robots: { index: false, follow: true },
};

export default function DocsPage() {
  return (
    <ComingSoonPage
      eyebrow="DOCUMENTATION"
      headline="Learn how Fivvle validates."
      body="A structured walkthrough of the research pipeline, the five acts, evidence sourcing, and the Verdict model is coming soon. If you have specific questions, the fastest path is to start a validation and see it work."
      ctaLabel="START A VALIDATION →"
      ctaHref="/login?intent=start"
      showEmailCapture={false}
    />
  );
}

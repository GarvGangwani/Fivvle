import type { Metadata } from "next";
import { ComingSoonPage } from "@/components/marketing/ComingSoonPage";

export const metadata: Metadata = {
  title: "Changelog — Fivvle",
  description:
    "Structured versioned changelog for Fivvle — ship notes and release history coming soon.",
  robots: { index: false, follow: true },
};

export default function ChangelogPage() {
  return (
    <ComingSoonPage
      eyebrow="CHANGELOG"
      headline="What's new in Fivvle."
      body="We're building in the open. A structured, versioned changelog is on the way. For now, follow the ship notes on our socials."
      ctaLabel="NOTIFY ME"
      ctaHref="/waitlist?intent=changelog"
      showEmailCapture
      intent="changelog"
    />
  );
}

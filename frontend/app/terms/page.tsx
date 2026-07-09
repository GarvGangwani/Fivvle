import type { Metadata } from "next";
import { ComingSoonPage } from "@/components/marketing/ComingSoonPage";

export const metadata: Metadata = {
  title: "Terms of Service — Fivvle",
  description:
    "Fivvle terms of service — platform rules and validation report disclaimers.",
  robots: { index: false, follow: true },
};

// TODO: replace mailto with real legal contact address before merge
const LEGAL_CONTACT = "mailto:legal@fivvle.io";

export default function TermsPage() {
  return (
    <ComingSoonPage
      eyebrow="TERMS OF SERVICE"
      headline="The rules of the road."
      body="Our full terms of service are being finalized with counsel. By using Fivvle, you agree to use the platform lawfully, respect intellectual property, and understand that validation reports are directional — not financial or legal advice."
      ctaLabel="CONTACT LEGAL"
      ctaHref={LEGAL_CONTACT}
    />
  );
}

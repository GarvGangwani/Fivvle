import type { Metadata } from "next";
import { ComingSoonPage } from "@/components/marketing/ComingSoonPage";

export const metadata: Metadata = {
  title: "Privacy Policy — Fivvle",
  description:
    "Fivvle privacy policy — how we handle your data, validations, and deletion requests.",
  robots: { index: false, follow: true },
};

// TODO: replace mailto with real privacy contact address before merge
const PRIVACY_CONTACT = "mailto:privacy@fivvle.io";

export default function PrivacyPage() {
  return (
    <ComingSoonPage
      eyebrow="PRIVACY POLICY"
      headline="Your data. Your evidence. Your call."
      body="Our full privacy policy is being finalized with counsel. Short version: we don't sell your data, we don't train on your validations, and we delete on request. Full document coming shortly."
      ctaLabel="CONTACT PRIVACY"
      ctaHref={PRIVACY_CONTACT}
    />
  );
}

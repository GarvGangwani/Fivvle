"use client";

import { useParams } from "next/navigation";
import { LandingPageRuntimeWorkspace } from "@/components/landing-runtime-v2/LandingPageRuntimeWorkspace";

export default function LandingPageRuntimePage() {
  const params = useParams<{ id: string }>();
  return <LandingPageRuntimeWorkspace experimentId={params.id} />;
}

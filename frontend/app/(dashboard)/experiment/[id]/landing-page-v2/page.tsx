"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { LoadingState } from "@/components/ui/LoadingState";

/** Legacy route — redirects to landing-page-runtime. */
export default function LandingPageV2RedirectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/experiment/${params.id}/landing-page-runtime`);
  }, [params.id, router]);

  return <LoadingState label="Redirecting to landing page runtime…" />;
}

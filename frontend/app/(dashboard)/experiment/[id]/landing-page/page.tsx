"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";

export default function LandingPageEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const experimentId = params.id;

  useEffect(() => {
    router.replace(`/experiment/${experimentId}?stage=landing`);
  }, [experimentId, router]);

  return (
    <div
      className="flex min-h-[40vh] items-center justify-center px-6 py-12"
      aria-busy="true"
      aria-label="Opening launch"
    >
      <BrutalistSkeleton variant="card" height="h-40" width="w-full" className="max-w-md" />
    </div>
  );
}

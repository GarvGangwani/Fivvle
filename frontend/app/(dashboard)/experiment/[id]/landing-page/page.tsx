"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { EditorLoadingSkeleton } from "@/components/landing-page-editor/EditorLoadingSkeleton";

export default function LandingPageEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const experimentId = params.id;

  useEffect(() => {
    router.replace(`/experiment/${experimentId}?stage=landing`);
  }, [experimentId, router]);

  return <EditorLoadingSkeleton />;
}

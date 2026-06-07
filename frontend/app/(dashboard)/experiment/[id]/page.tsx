"use client";

import { ExperimentDetailPanel } from "@/components/dashboard/ExperimentDetailPanel";
import { useParams } from "next/navigation";

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
      <ExperimentDetailPanel experimentId={params.id} />
    </main>
  );
}

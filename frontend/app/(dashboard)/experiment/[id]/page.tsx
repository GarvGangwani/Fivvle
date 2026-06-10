"use client";

import { ExperimentDetailPanel } from "@/components/dashboard/ExperimentDetailPanel";
import { useParams } from "next/navigation";

export default function ExperimentDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <main className="flex h-[calc(100vh-4rem)] flex-col px-4 py-4 sm:px-6">
      <ExperimentDetailPanel experimentId={params.id} />
    </main>
  );
}

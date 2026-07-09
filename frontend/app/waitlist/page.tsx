import { Suspense } from "react";
import { WaitlistForm } from "./WaitlistForm";

export default function WaitlistPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-canvas-bg px-gutter pt-28 font-body-md text-ink-secondary">
          Loading…
        </div>
      }
    >
      <WaitlistForm />
    </Suspense>
  );
}

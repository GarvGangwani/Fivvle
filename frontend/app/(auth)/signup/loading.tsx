import { BrutalistSkeleton } from "@/components/ui/BrutalistSkeleton";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthCard } from "@/components/auth/AuthCard";

/** Signup route pending UI — matches AuthLayout + AuthCard form shape. */
export default function SignupLoading() {
  return (
    <AuthLayout>
      <AuthCard>
        <div aria-busy="true" aria-label="Loading signup">
          <BrutalistSkeleton variant="block" height="h-10" width="w-48" />
          <BrutalistSkeleton
            variant="line"
            width="w-4/5"
            className="mt-4"
          />
          <BrutalistSkeleton
            variant="block"
            height="h-12"
            className="mt-8"
          />
          <BrutalistSkeleton
            variant="line"
            width="w-1/3"
            className="mx-auto mt-6"
          />
          <BrutalistSkeleton
            variant="block"
            height="h-12"
            className="mt-6"
          />
          <BrutalistSkeleton
            variant="block"
            height="h-12"
            className="mt-3"
          />
          <BrutalistSkeleton
            variant="block"
            height="h-12"
            className="mt-3"
          />
          <BrutalistSkeleton
            variant="block"
            height="h-12"
            className="mt-6"
          />
        </div>
      </AuthCard>
    </AuthLayout>
  );
}

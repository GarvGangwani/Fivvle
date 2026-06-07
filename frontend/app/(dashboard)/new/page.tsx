import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ChatInterface } from "@/components/chat/ChatInterface";

export default function NewExperimentPage() {
  return (
    <div className="flex h-[100dvh] flex-col">
      <div className="border-b border-gray-200 bg-white px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 transition-colors hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Back to dashboard</span>
          </Link>
          <h1 className="text-sm font-semibold text-gray-900 sm:text-base">
            New idea
          </h1>
        </div>
      </div>

      <ChatInterface />
    </div>
  );
}

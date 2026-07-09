import Link from "next/link";
import { marketingButtonClass } from "./marketing-styles";

export function MobileComposerPill() {
  return (
    <div className="fixed bottom-8 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 md:hidden">
      <Link
        href="/new"
        className={`${marketingButtonClass} flex w-full items-center justify-center gap-2 rounded-full border-2 border-border-master bg-brand-primary px-6 py-4 font-label-md text-label-md uppercase text-ink-inverse shadow-brutal-md no-underline`}
      >
        <span className="material-symbols-outlined" aria-hidden="true">
          auto_awesome
        </span>
        START A VALIDATION
      </Link>
    </div>
  );
}

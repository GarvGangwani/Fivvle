"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  disabled?: boolean;
  children: ReactNode;
  headerActions?: ReactNode;
}

export function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  disabled,
  children,
  headerActions,
}: CollapsibleSectionProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const isOpen = controlledOpen ?? uncontrolledOpen;
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (isOpen) {
      sectionRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [isOpen]);

  const toggle = () => {
    if (disabled) return;
    const next = !isOpen;
    if (controlledOpen === undefined) {
      setUncontrolledOpen(next);
    }
    onOpenChange?.(next);
  };

  return (
    <section
      ref={sectionRef}
      className={`lp-collapse${isOpen ? " lp-collapse-open" : ""}`}
    >
      <button
        type="button"
        className="lp-collapse-trigger"
        onClick={toggle}
        disabled={disabled}
        aria-expanded={isOpen}
      >
        <span className="lp-collapse-leading">
          <span className="lp-collapse-title">{title}</span>
          {!isOpen && summary ? (
            <span className="lp-collapse-summary">{summary}</span>
          ) : null}
        </span>
        <ChevronDown
          className={`lp-collapse-chevron ${isOpen ? "lp-collapse-chevron-open" : ""}`}
          aria-hidden
        />
      </button>
      {isOpen ? (
        <div className="lp-collapse-body">
          {headerActions ? (
            <div className="lp-collapse-actions">{headerActions}</div>
          ) : null}
          {children}
        </div>
      ) : null}
    </section>
  );
}

import { useEffect, useRef, useState, type RefObject } from "react";

function getScrollParent(element: HTMLElement): Element | null {
  let parent = element.parentElement;
  while (parent) {
    const { overflowY } = getComputedStyle(parent);
    if (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") {
      return parent;
    }
    parent = parent.parentElement;
  }
  return null;
}

/**
 * Scroll-reveal driven by React state so re-renders (FAQ toggles, copy edits)
 * do not strip visibility classes added imperatively via classList.
 */
export function useScrollReveal(
  rootRef: RefObject<HTMLElement | null>,
  deps: readonly unknown[] = [],
) {
  const [revealedIds, setRevealedIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const revealedIdsRef = useRef(revealedIds);
  revealedIdsRef.current = revealedIds;

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !("IntersectionObserver" in window)) return;

    const scrollRoot = getScrollParent(root);
    const elements = root.querySelectorAll<HTMLElement>("[data-scroll-reveal]");

    const io = new IntersectionObserver(
      (entries) => {
        const next = new Set(revealedIdsRef.current);
        let changed = false;
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const id = entry.target.getAttribute("data-scroll-reveal");
          if (!id || next.has(id)) continue;
          next.add(id);
          changed = true;
          io.unobserve(entry.target);
        }
        if (changed) {
          setRevealedIds(next);
        }
      },
      {
        threshold: 0.12,
        root: scrollRoot,
      },
    );

    elements.forEach((el) => io.observe(el));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller controls when to rebind
  }, deps);

  const revealProps = (id: string) => ({
    "data-scroll-reveal": id,
  });

  const revealClass = (
    id: string,
    hiddenClass: string,
    visibleClass: string,
  ): string => (revealedIds.has(id) ? visibleClass : hiddenClass);

  return { revealedIds, revealProps, revealClass };
}

/** Nearest scrollable ancestor, or window. */
export function getScrollParent(node: HTMLElement | null): HTMLElement | Window {
  let el = node?.parentElement ?? null;
  while (el) {
    const { overflowY } = getComputedStyle(el);
    if (
      (overflowY === "auto" || overflowY === "scroll") &&
      el.scrollHeight > el.clientHeight
    ) {
      return el;
    }
    el = el.parentElement;
  }
  return window;
}

function scrollContainerToTop(container: HTMLElement | Window): void {
  if (container === window) {
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  container.scrollTo({ top: 0, behavior: "smooth" });
}

/** Smooth-scroll to an in-page hash (`#section` or `#top`). */
export function smoothScrollToHash(
  hash: string,
  root?: HTMLElement | null,
): boolean {
  const raw = hash.trim();
  if (!raw.startsWith("#")) return false;
  const id = raw.slice(1);
  if (!id) return false;

  if (id === "top") {
    const anchor = root ?? document.documentElement;
    scrollContainerToTop(getScrollParent(anchor));
    return true;
  }

  const escaped = CSS.escape(id);
  const target =
    root?.querySelector<HTMLElement>(`#${escaped}`) ??
    document.getElementById(id);
  if (!target) return false;

  target.scrollIntoView({ behavior: "smooth", block: "start" });
  return true;
}

/** Intercept same-page `#` links inside `root` for smooth scrolling. */
export function bindSmoothScrollAnchors(root: HTMLElement): () => void {
  const onClick = (event: MouseEvent) => {
    if (event.defaultPrevented) return;
    if (event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    const anchor = (event.target as Element | null)?.closest?.(
      'a[href^="#"]',
    );
    if (!(anchor instanceof HTMLAnchorElement)) return;

    const href = anchor.getAttribute("href");
    if (!href || href === "#") return;

    const id = href.slice(1);
    const inRoot =
      id === "top" ||
      root.querySelector(`#${CSS.escape(id)}`) != null ||
      document.getElementById(id) != null;
    if (!inRoot) return;

    event.preventDefault();
    smoothScrollToHash(href, root);
  };

  root.addEventListener("click", onClick);
  return () => root.removeEventListener("click", onClick);
}

interface RazorpayBrandProps {
  className?: string;
  /** When true, only the mark is shown (no "Razorpay" text). */
  markOnly?: boolean;
}

/** Razorpay wordmark + icon for checkout trust copy. */
export function RazorpayBrand({ className = "", markOnly = false }: RazorpayBrandProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
        className="shrink-0"
      >
        <path
          d="M4 20V4h3.2l4.1 9.4L15.4 4H18.5v16h-2.6V10.1L12.2 18h-1.5L8.1 10.1V20H4Z"
          fill="#072654"
        />
        <path
          d="M19.2 4h2.8v16h-2.8V4Z"
          fill="#3395FF"
        />
      </svg>
      {!markOnly ? (
        <span className="font-medium text-[var(--fv-text-soft)]">Razorpay</span>
      ) : null}
    </span>
  );
}

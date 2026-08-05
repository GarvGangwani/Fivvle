import { getInitials } from "./dashboard-helpers";

type Size = "sm" | "md" | "lg";

const SIZE_MAP: Record<Size, { outer: string; inner: string; text: string }> = {
  sm: { outer: "w-10 h-10 p-1", inner: "w-full h-full", text: "text-sm" },
  md: { outer: "w-14 h-14 p-1.5", inner: "w-full h-full", text: "text-lg" },
  lg: { outer: "w-24 h-24 p-2", inner: "w-full h-full", text: "text-2xl" },
};

type Props = {
  photoURL: string | null | undefined;
  displayName: string | null | undefined;
  size?: Size;
  className?: string;
};

export function ProfileAvatar({
  photoURL,
  displayName,
  size = "md",
  className = "",
}: Props) {
  const sizing = SIZE_MAP[size];
  const initials = getInitials(displayName ?? "") || "?";

  return (
    <div
      className={`rounded-full bg-brand-primary-soft ${sizing.outer} ${className}`}
      aria-label={displayName ? `Profile: ${displayName}` : "Profile"}
    >
      <div
        className={`${sizing.inner} flex items-center justify-center overflow-hidden rounded-full border-2 border-surface-card bg-surface-card`}
      >
        {photoURL ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photoURL}
            alt=""
            className="h-full w-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <span
            className={`font-headline-md ${sizing.text} font-bold text-accent`}
          >
            {initials}
          </span>
        )}
      </div>
    </div>
  );
}

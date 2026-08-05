"use client";

import Image from "next/image";
import {
  getUserInitial,
  isSafeAvatarUrl,
} from "@/lib/user-avatar";

const SIZE_CLASSES = {
  sm: "h-9 w-9 text-xs",
  md: "h-10 w-10 text-sm",
} as const;

interface UserAvatarProps {
  displayName?: string | null;
  email?: string | null;
  photoUrl?: string | null;
  size?: keyof typeof SIZE_CLASSES;
  className?: string;
}

export function UserAvatar({
  displayName,
  email,
  photoUrl,
  size = "sm",
  className = "",
}: UserAvatarProps) {
  const initial = getUserInitial(displayName, email);
  const sizeClass = SIZE_CLASSES[size];

  if (isSafeAvatarUrl(photoUrl)) {
    return (
      <div
        className={`relative shrink-0 overflow-hidden rounded-full bg-accent-muted ${sizeClass} ${className}`}
      >
        <Image
          src={photoUrl}
          alt=""
          fill
          sizes={size === "sm" ? "36px" : "40px"}
          className="object-cover"
          referrerPolicy="no-referrer"
        />
      </div>
    );
  }

  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full bg-accent-muted font-semibold text-accent ${sizeClass} ${className}`}
      aria-hidden={!displayName && !email}
    >
      {initial}
    </div>
  );
}

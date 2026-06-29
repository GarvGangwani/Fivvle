import Image from "next/image";

interface FivvleLogoProps {
  size?: number;
  className?: string;
}

export function FivvleLogo({ size = 30, className = "" }: FivvleLogoProps) {
  return (
    <Image
      src="/fivvle-icon.png"
      alt=""
      width={size}
      height={size}
      className={`shrink-0 rounded-lg ${className}`}
      aria-hidden
    />
  );
}

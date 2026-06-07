import Image from "next/image";

interface FivvleLogoProps {
  size?: number;
  className?: string;
}

export function FivvleLogo({ size = 30, className = "" }: FivvleLogoProps) {
  return (
    <Image
      src="/fivvle-logo.png"
      alt="Fivvle"
      width={size}
      height={size}
      className={className}
      priority
    />
  );
}

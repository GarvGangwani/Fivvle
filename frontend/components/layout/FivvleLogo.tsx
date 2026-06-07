interface FivvleLogoProps {
  size?: number;
  className?: string;
}

export function FivvleLogo({ size = 30, className = "" }: FivvleLogoProps) {
  const fontSize = size <= 22 ? 11 : 16;
  return (
    <div
      className={`fv-f-logo ${className}`}
      style={{ width: size, height: size, fontSize }}
      aria-hidden
    >
      F
    </div>
  );
}

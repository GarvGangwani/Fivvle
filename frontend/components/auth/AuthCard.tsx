interface AuthCardProps {
  children: React.ReactNode;
  size?: "default" | "wide";
}

export function AuthCard({ children, size = "default" }: AuthCardProps) {
  const widthClass =
    size === "wide" ? "max-w-[560px]" : "max-w-[480px]";

  return (
    <div
      className={`w-full rounded-lg border-2 border-border-master bg-surface-card p-8 shadow-brutal-lg ${widthClass}`}
    >
      {children}
    </div>
  );
}

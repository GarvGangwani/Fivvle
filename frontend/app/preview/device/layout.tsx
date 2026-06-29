export default function DevicePreviewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-0 bg-transparent" style={{ margin: 0, padding: 0 }}>
      {children}
    </div>
  );
}

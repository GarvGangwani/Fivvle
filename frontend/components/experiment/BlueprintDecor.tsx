export function BlueprintDecor() {
  return (
    <>
      <div
        className="absolute pointer-events-none select-none"
        style={{ left: "-4%", bottom: "8%", opacity: 0.12, transform: "rotate(12deg)" }}
      >
        <div className="border-2 border-ink-primary p-4 w-56 bg-canvas-bg">
          <p className="font-mono text-mono-sm leading-tight text-ink-primary">
            SYSTEM_ARCH_V2.01
            <br />
            LATENCY: 42MS
            <br />
            THROUGHPUT: HIGH
            <br />
            RED_NODES: 0
          </p>
        </div>
      </div>

      <div
        className="absolute pointer-events-none select-none"
        style={{ right: "-2%", top: "8%", opacity: 0.12 }}
      >
        <div className="border-2 border-dashed border-ink-primary w-32 h-32" />
      </div>
    </>
  );
}

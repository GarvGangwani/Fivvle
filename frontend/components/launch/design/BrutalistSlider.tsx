"use client";

type Props = {
  label: string;
  hint?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  formatValue?: (value: number) => string;
  onChange: (value: number) => void;
};

/** Brutalist range input for Launch Design panels. */
export function BrutalistSlider({
  label,
  hint,
  value,
  min = 0,
  max = 100,
  step = 1,
  disabled,
  formatValue,
  onChange,
}: Props) {
  const display = formatValue ? formatValue(value) : `${value}%`;

  return (
    <div className={disabled ? "opacity-40" : undefined}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-label-sm text-label-sm uppercase tracking-wider text-ink-primary">
            {label}
          </p>
          {hint ? (
            <p className="mt-0.5 font-mono text-mono-sm uppercase text-ink-primary/50">
              {hint}
            </p>
          ) : null}
        </div>
        <span className="shrink-0 border-2 border-border-master bg-brutalist-yellow px-2 py-0.5 font-mono text-mono-sm text-ink-primary">
          {display}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={display}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none border-2 border-border-master bg-surface-elevated accent-ink-primary disabled:cursor-not-allowed"
      />
    </div>
  );
}

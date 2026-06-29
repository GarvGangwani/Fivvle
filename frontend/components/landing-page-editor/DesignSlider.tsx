"use client";

import type { CSSProperties } from "react";

interface DesignSliderProps {
  label: string;
  hint?: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  formatValue?: (value: number) => string;
  onChange: (value: number) => void;
}

export function DesignSlider({
  label,
  hint,
  value,
  min = 0,
  max = 100,
  step = 1,
  disabled,
  formatValue,
  onChange,
}: DesignSliderProps) {
  const display = formatValue ? formatValue(value) : `${value}%`;
  const fillPercent =
    max === min ? 0 : ((value - min) / (max - min)) * 100;

  return (
    <div className={`lp-design-slider${disabled ? " lp-design-slider-disabled" : ""}`}>
      <div className="lp-design-slider-header">
        <div className="min-w-0">
          <p className="lp-design-slider-label">{label}</p>
          {hint ? <p className="lp-design-slider-hint">{hint}</p> : null}
        </div>
        <span className="lp-design-slider-value" aria-hidden>
          {display}
        </span>
      </div>
      <input
        type="range"
        className="lp-design-slider-input"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        style={{ "--slider-fill": `${fillPercent}%` } as CSSProperties}
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={display}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

"use client";

// ---------------------------------------------------------------------------
// ThresholdSlider – stretch feature.
// Lets the demo audience drag a minimum-confidence threshold and watch the
// result list update in real time. Highest-visibility live-demo differentiator.
// ---------------------------------------------------------------------------

interface ThresholdSliderProps {
  value: number; // 0–1
  onChange: (value: number) => void;
}

export default function ThresholdSlider({ value, onChange }: ThresholdSliderProps) {
  const pct = Math.round(value * 100);

  let label = "High confidence";
  let labelClass = "threshold-label--high";
  if (value < 0.4) {
    label = "Low confidence";
    labelClass = "threshold-label--low";
  } else if (value < 0.7) {
    label = "Medium confidence";
    labelClass = "threshold-label--medium";
  }

  return (
    <div className="threshold-slider-wrapper" id="threshold-slider">
      <label htmlFor="confidence-threshold" className="threshold-slider-label">
        Minimum confidence threshold:{" "}
        <span className={`threshold-value ${labelClass}`}>{pct}%</span>
        <span className="threshold-desc">{label}</span>
      </label>
      <input
        id="confidence-threshold"
        type="range"
        min={0}
        max={100}
        step={5}
        value={pct}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="threshold-range"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={`${pct}% – ${label}`}
      />
      <div className="threshold-ticks" aria-hidden="true">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
    </div>
  );
}

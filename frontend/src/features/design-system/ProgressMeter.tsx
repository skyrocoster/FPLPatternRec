import { Meter } from "@base-ui/react/meter";

import styles from "./ProgressMeter.module.css";

export type ProgressMeterProps = {
  /** Determinate value in the [min, max] range. Null means unavailable: no meter role. */
  value: number | null;
  min?: number;
  max?: number;
  /** Accessible name for the determinate meter. */
  label: string;
  /** Accessible value text, e.g. "75%". Defaults to a rounded percent of the range. */
  valueText?: string;
  className?: string;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * Shared determinate progress display. A null value renders a truthful
 * unavailable track without a meter ARIA contract.
 */
export function ProgressMeter({
  value,
  min = 0,
  max = 100,
  label,
  valueText,
  className,
}: ProgressMeterProps) {
  if (value === null || Number.isNaN(value)) {
    return (
      <div
        className={[styles.meter, styles.unavailable, className].filter(Boolean).join(" ")}
        data-state="unavailable"
      >
        <div className={styles.track} aria-hidden="true">
          <span className={styles.indicator} style={{ inlineSize: "0%" }} />
        </div>
        <span className={styles.unavailableLabel}>{valueText ?? "No data"}</span>
      </div>
    );
  }

  const clamped = clamp(value, min, max);
  const percent = max === min ? 0 : ((clamped - min) / (max - min)) * 100;
  const text = valueText ?? `${Math.round(percent)}%`;

  return (
    <Meter.Root
      className={[styles.meter, className].filter(Boolean).join(" ")}
      min={min}
      max={max}
      value={Math.round(clamped * 100) / 100}
      aria-valuetext={text}
      data-state="determinate"
    >
      <Meter.Label className={styles.visuallyHidden}>{label}</Meter.Label>
      <Meter.Track className={styles.track}>
        <Meter.Indicator className={styles.indicator} style={{ inlineSize: `${percent}%` }} />
      </Meter.Track>
    </Meter.Root>
  );
}

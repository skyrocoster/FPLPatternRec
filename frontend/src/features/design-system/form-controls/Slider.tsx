import { Slider as BaseSlider } from "@base-ui/react/slider";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export type SliderValue = number | readonly number[];

export interface SliderProps extends Omit<
  ComponentPropsWithoutRef<"div">,
  "defaultValue" | "onChange"
> {
  label: ReactNode;
  value?: SliderValue;
  defaultValue?: SliderValue;
  onValueChange?: (value: SliderValue) => void;
  onValueCommitted?: (value: SliderValue) => void;
  min?: number;
  max?: number;
  step?: number;
  largeStep?: number;
  minStepsBetweenValues?: number;
  disabled?: boolean;
  orientation?: "horizontal" | "vertical";
  name?: string;
  format?: Intl.NumberFormatOptions;
  locale?: Intl.LocalesArgument;
  showValue?: boolean;
  thumbAriaLabel?: string | readonly string[];
}

/** Single-value or range slider with project styling and optional value readout. */
export function Slider({
  label,
  value,
  defaultValue,
  onValueChange,
  onValueCommitted,
  min,
  max,
  step,
  largeStep,
  minStepsBetweenValues,
  disabled,
  orientation = "horizontal",
  name,
  format,
  locale,
  showValue = true,
  thumbAriaLabel,
  className,
  ...rest
}: SliderProps) {
  const currentShape = value ?? defaultValue;
  const thumbCount = Array.isArray(currentShape) ? Math.max(1, currentShape.length) : 1;

  return (
    <BaseSlider.Root<SliderValue>
      {...rest}
      className={[styles.sliderField, className].filter(Boolean).join(" ")}
      value={value}
      defaultValue={defaultValue}
      onValueChange={(nextValue) => onValueChange?.(nextValue)}
      onValueCommitted={(nextValue) => onValueCommitted?.(nextValue)}
      min={min}
      max={max}
      step={step}
      largeStep={largeStep}
      minStepsBetweenValues={minStepsBetweenValues}
      disabled={disabled}
      orientation={orientation}
      name={name}
      format={format}
      locale={locale}
    >
      <div className={styles.sliderHeading}>
        <BaseSlider.Label className={styles.sliderLabel}>{label}</BaseSlider.Label>
        {showValue ? <BaseSlider.Value className={styles.sliderValue} /> : null}
      </div>
      <BaseSlider.Control className={styles.sliderControl}>
        <BaseSlider.Track className={styles.sliderTrack}>
          <BaseSlider.Indicator className={styles.sliderIndicator} />
        </BaseSlider.Track>
        {Array.from({ length: thumbCount }, (_, index) => (
          <BaseSlider.Thumb
            className={styles.sliderThumb}
            key={index}
            aria-label={
              Array.isArray(thumbAriaLabel)
                ? thumbAriaLabel[index]
                : (thumbAriaLabel ?? (thumbCount > 1 ? `Value ${index + 1}` : undefined))
            }
          />
        ))}
      </BaseSlider.Control>
    </BaseSlider.Root>
  );
}

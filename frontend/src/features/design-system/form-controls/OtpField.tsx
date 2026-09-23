import { OTPField as BaseOtpField } from "@base-ui/react/otp-field";
import type { OTPFieldRootProps } from "@base-ui/react/otp-field";
import { useId } from "react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface OtpFieldProps extends Omit<
  OTPFieldRootProps,
  "children" | "className" | "id" | "onValueChange"
> {
  label: ReactNode;
  description?: ReactNode;
  id?: string;
  onValueChange?: (value: string) => void;
  /** Accessible names for slots after the first; the visible field label names the first slot. */
  slotAriaLabel?: (index: number, length: number) => string;
  inputProps?: Omit<
    ComponentPropsWithoutRef<"input">,
    "aria-describedby" | "aria-label" | "defaultValue" | "id" | "maxLength" | "value"
  >;
  className?: string;
}

/** Labeled one-time-code field with an accessible input for each character. */
export function OtpField({
  label,
  description,
  id: idProp,
  length,
  onValueChange,
  slotAriaLabel = (index, slotCount) => `Character ${index + 1} of ${slotCount}`,
  inputProps,
  className,
  ...rootProps
}: OtpFieldProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const descriptionId = description ? `${id}-description` : undefined;

  return (
    <div className={[styles.otpField, className].filter(Boolean).join(" ")}>
      <label className={styles.controlLabel} htmlFor={id}>
        {label}
      </label>
      <BaseOtpField.Root
        {...rootProps}
        id={id}
        length={length}
        aria-describedby={descriptionId}
        className={styles.otpRoot}
        onValueChange={(nextValue) => onValueChange?.(nextValue)}
      >
        {Array.from({ length }, (_, index) => (
          <BaseOtpField.Input
            {...inputProps}
            key={index}
            className={styles.otpInput}
            aria-describedby={descriptionId}
            aria-label={index === 0 ? undefined : slotAriaLabel(index, length)}
          />
        ))}
      </BaseOtpField.Root>
      {description ? (
        <p className={styles.description} id={descriptionId}>
          {description}
        </p>
      ) : null}
    </div>
  );
}

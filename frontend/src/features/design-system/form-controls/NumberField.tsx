import { NumberField as BaseNumberField } from "@base-ui/react/number-field";
import type { NumberFieldRootProps } from "@base-ui/react/number-field";
import { Minus, Plus } from "lucide-react";
import { useId } from "react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface NumberFieldProps extends Omit<
  NumberFieldRootProps,
  "className" | "id" | "onValueChange"
> {
  label: ReactNode;
  description?: ReactNode;
  id?: string;
  onValueChange?: (value: number | null) => void;
  inputProps?: Omit<ComponentPropsWithoutRef<"input">, "defaultValue" | "id" | "value">;
  decrementLabel?: string;
  incrementLabel?: string;
  className?: string;
}

/** Numeric field with accessible decrement and increment controls. */
export function NumberField({
  label,
  description,
  id: idProp,
  onValueChange,
  inputProps,
  decrementLabel = "Decrease value",
  incrementLabel = "Increase value",
  className,
  ...rootProps
}: NumberFieldProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;

  return (
    <BaseNumberField.Root
      {...rootProps}
      id={id}
      className={[styles.numberField, className].filter(Boolean).join(" ")}
      onValueChange={(nextValue) => onValueChange?.(nextValue)}
    >
      <label className={styles.controlLabel} htmlFor={id}>
        {label}
      </label>
      {description ? <span className={styles.description}>{description}</span> : null}
      <BaseNumberField.Group className={styles.numberGroup}>
        <BaseNumberField.Decrement className={styles.numberButton} aria-label={decrementLabel}>
          <Minus aria-hidden="true" />
        </BaseNumberField.Decrement>
        <BaseNumberField.Input {...inputProps} className={styles.numberInput} />
        <BaseNumberField.Increment className={styles.numberButton} aria-label={incrementLabel}>
          <Plus aria-hidden="true" />
        </BaseNumberField.Increment>
      </BaseNumberField.Group>
    </BaseNumberField.Root>
  );
}

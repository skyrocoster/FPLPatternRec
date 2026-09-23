import { Switch as BaseSwitch } from "@base-ui/react/switch";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface SwitchProps extends Omit<
  ComponentPropsWithoutRef<"span">,
  "children" | "onChange"
> {
  label: ReactNode;
  description?: ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  name?: string;
  value?: string;
  uncheckedValue?: string;
}

/** Labeled on/off control built on Base UI Switch. */
export function Switch({
  label,
  description,
  checked,
  defaultChecked,
  onCheckedChange,
  disabled,
  readOnly,
  required,
  name,
  value,
  uncheckedValue,
  className,
  ...rest
}: SwitchProps) {
  return (
    <label className={[styles.switchField, className].filter(Boolean).join(" ")}>
      <BaseSwitch.Root
        {...rest}
        className={styles.switchRoot}
        checked={checked}
        defaultChecked={defaultChecked}
        onCheckedChange={(nextChecked) => onCheckedChange?.(nextChecked)}
        disabled={disabled}
        readOnly={readOnly}
        required={required}
        name={name}
        value={value}
        uncheckedValue={uncheckedValue}
      >
        <BaseSwitch.Thumb className={styles.switchThumb} />
      </BaseSwitch.Root>
      <span className={styles.switchCopy}>
        <span className={styles.controlLabel}>{label}</span>
        {description ? <span className={styles.optionDescription}>{description}</span> : null}
      </span>
    </label>
  );
}

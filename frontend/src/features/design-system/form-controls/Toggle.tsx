import { Toggle as BaseToggle } from "@base-ui/react/toggle";
import type { ComponentPropsWithoutRef } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface ToggleProps extends Omit<
  ComponentPropsWithoutRef<"button">,
  "defaultValue" | "onChange"
> {
  pressed?: boolean;
  defaultPressed?: boolean;
  onPressedChange?: (pressed: boolean) => void;
  value?: string;
}

/** Two-state button that also composes with ToggleGroup. */
export function Toggle({
  pressed,
  defaultPressed,
  onPressedChange,
  value,
  className,
  type = "button",
  ...rest
}: ToggleProps) {
  return (
    <BaseToggle
      {...rest}
      type={type}
      className={[styles.toggle, className].filter(Boolean).join(" ")}
      pressed={pressed}
      defaultPressed={defaultPressed}
      onPressedChange={(nextPressed) => onPressedChange?.(nextPressed)}
      value={value}
    />
  );
}

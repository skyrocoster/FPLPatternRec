import { ToggleGroup as BaseToggleGroup } from "@base-ui/react/toggle-group";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { Toggle } from "./Toggle";
import styles from "./AdvancedFormControls.module.css";

export interface ToggleOptionDefinition {
  value: string;
  label: ReactNode;
  disabled?: boolean;
  ariaLabel?: string;
}

export interface ToggleGroupProps extends Omit<
  ComponentPropsWithoutRef<"div">,
  "defaultValue" | "onChange"
> {
  options: readonly ToggleOptionDefinition[];
  value?: readonly string[];
  defaultValue?: readonly string[];
  onValueChange?: (value: string[]) => void;
  multiple?: boolean;
  disabled?: boolean;
  orientation?: "horizontal" | "vertical";
  loopFocus?: boolean;
}

/** Keyboard-navigable group of one or more pressed-state buttons. */
export function ToggleGroup({
  options,
  value,
  defaultValue,
  onValueChange,
  multiple,
  disabled,
  orientation = "horizontal",
  loopFocus,
  className,
  ...rest
}: ToggleGroupProps) {
  return (
    <BaseToggleGroup
      {...rest}
      className={[styles.toggleGroup, className].filter(Boolean).join(" ")}
      value={value}
      defaultValue={defaultValue}
      onValueChange={(nextValue) => onValueChange?.(nextValue)}
      multiple={multiple}
      disabled={disabled}
      orientation={orientation}
      loopFocus={loopFocus}
    >
      {options.map((option) => (
        <Toggle
          key={option.value}
          value={option.value}
          disabled={option.disabled}
          aria-label={option.ariaLabel}
        >
          {option.label}
        </Toggle>
      ))}
    </BaseToggleGroup>
  );
}

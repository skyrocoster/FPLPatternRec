import { Checkbox } from "@base-ui/react/checkbox";
import { CheckboxGroup as BaseCheckboxGroup } from "@base-ui/react/checkbox-group";
import { Check } from "lucide-react";
import { useId } from "react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface CheckboxOptionDefinition {
  value: string;
  label: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}

export interface CheckboxGroupProps extends Omit<
  ComponentPropsWithoutRef<"div">,
  "defaultValue" | "onChange"
> {
  label: ReactNode;
  options: readonly CheckboxOptionDefinition[];
  value?: string[];
  defaultValue?: string[];
  onValueChange?: (value: string[]) => void;
  name?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  description?: ReactNode;
}

/** Reusable labeled group of Base UI checkboxes. */
export function CheckboxGroup({
  label,
  options,
  value,
  defaultValue,
  onValueChange,
  name,
  disabled,
  readOnly,
  required,
  description,
  className,
  ...rest
}: CheckboxGroupProps) {
  const labelId = useId();

  return (
    <div className={[styles.checkboxField, className].filter(Boolean).join(" ")}>
      <span className={styles.controlLabel} id={labelId}>
        {label}
      </span>
      {description ? <span className={styles.description}>{description}</span> : null}
      <BaseCheckboxGroup
        {...rest}
        aria-labelledby={labelId}
        className={styles.checkboxGroup}
        value={value}
        defaultValue={defaultValue}
        onValueChange={(nextValue) => onValueChange?.(nextValue)}
        allValues={options.map((option) => option.value)}
        disabled={disabled}
      >
        {options.map((option) => (
          <label
            className={styles.checkboxOption}
            data-disabled={disabled || option.disabled ? "" : undefined}
            key={option.value}
          >
            <Checkbox.Root
              className={styles.checkboxRoot}
              value={option.value}
              name={name}
              disabled={disabled || option.disabled}
              readOnly={readOnly}
              required={required}
            >
              <Checkbox.Indicator className={styles.checkboxIndicator}>
                <Check aria-hidden="true" />
              </Checkbox.Indicator>
            </Checkbox.Root>
            <span className={styles.optionCopy}>
              <span>{option.label}</span>
              {option.description ? (
                <span className={styles.optionDescription}>{option.description}</span>
              ) : null}
            </span>
          </label>
        ))}
      </BaseCheckboxGroup>
    </div>
  );
}

import { Radio } from "@base-ui/react/radio";
import { RadioGroup as BaseRadioGroup } from "@base-ui/react/radio-group";
import { useId } from "react";

import styles from "./FormControls.module.css";

export interface RadioOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}

export interface RadioGroupProps {
  options: readonly RadioOption[];
  value: string;
  onValueChange: (value: string) => void;
  appearance?: "segmented" | "stacked";
  ariaLabel: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  name?: string;
}

export function RadioGroup({
  options,
  value,
  onValueChange,
  appearance = "segmented",
  ariaLabel,
  disabled,
  readOnly,
  required = true,
  name,
}: RadioGroupProps) {
  const groupId = useId();

  return (
    <BaseRadioGroup
      aria-label={ariaLabel}
      className={appearance === "segmented" ? styles.radioSegmented : styles.radioStacked}
      disabled={disabled}
      readOnly={readOnly}
      required={required}
      name={name}
      value={value}
      onValueChange={onValueChange}
    >
      {options.map((option, index) => {
        const optionLabelId = `${groupId}-option-${index}`;

        return (
          <label className={styles.radioLabel} key={option.value}>
            <Radio.Root
              aria-labelledby={optionLabelId}
              className={styles.radioRoot}
              disabled={option.disabled}
              value={option.value}
            >
              <Radio.Indicator className={styles.radioIndicator} />
            </Radio.Root>
            <span className={styles.radioCopy} id={optionLabelId}>
              <span>{option.label}</span>
              {option.description ? (
                <span className={styles.radioDescription}>{option.description}</span>
              ) : null}
            </span>
          </label>
        );
      })}
    </BaseRadioGroup>
  );
}

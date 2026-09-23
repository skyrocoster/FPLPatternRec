import { Field as BaseField } from "@base-ui/react/field";
import type { ReactNode } from "react";

import styles from "./FormControls.module.css";

export interface FieldProps {
  label: ReactNode;
  children: ReactNode;
  description?: ReactNode;
  error?: ReactNode;
  htmlFor?: string;
  name?: string;
  required?: boolean;
  disabled?: boolean;
  invalid?: boolean;
  className?: string;
}

/** Presentation-only field composition. Validation timing and form state stay external. */
export function Field({
  label,
  children,
  description,
  error,
  htmlFor,
  name,
  required = false,
  disabled = false,
  invalid = false,
  className,
}: FieldProps) {
  return (
    <BaseField.Root
      className={[styles.field, className].filter(Boolean).join(" ")}
      disabled={disabled}
      invalid={invalid}
      name={name}
    >
      <BaseField.Label className={styles.fieldLabel} htmlFor={htmlFor}>
        {label}
        {required ? (
          <span className={styles.requiredMark} aria-hidden="true">
            {" "}
            *
          </span>
        ) : null}
      </BaseField.Label>
      {description ? (
        <BaseField.Description className={styles.fieldDescription}>
          {description}
        </BaseField.Description>
      ) : null}
      {children}
      {error ? (
        <BaseField.Error className={styles.fieldError} match={invalid}>
          {error}
        </BaseField.Error>
      ) : null}
    </BaseField.Root>
  );
}

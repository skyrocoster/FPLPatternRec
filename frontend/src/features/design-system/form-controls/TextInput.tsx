import { Input } from "@base-ui/react/input";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./FormControls.module.css";

export type TextInputType = "text" | "search" | "email" | "url" | "tel" | "password";

export interface TextInputProps extends Omit<ComponentPropsWithoutRef<"input">, "type" | "size"> {
  type?: TextInputType;
  leading?: ReactNode;
  trailing?: ReactNode;
  invalid?: boolean;
}

export function TextInput({
  type = "text",
  leading,
  trailing,
  invalid = false,
  className,
  ...inputProps
}: TextInputProps) {
  return (
    <span className={styles.inputFrame} data-invalid={invalid || undefined}>
      {leading ? <span className={styles.inputSlot}>{leading}</span> : null}
      <Input
        {...inputProps}
        aria-invalid={invalid || undefined}
        className={[styles.textInput, className].filter(Boolean).join(" ")}
        type={type}
      />
      {trailing ? <span className={styles.inputSlot}>{trailing}</span> : null}
    </span>
  );
}

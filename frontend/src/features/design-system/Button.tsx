import { Button as BaseButton } from "@base-ui/react/button";
import type { ComponentPropsWithoutRef } from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "md" | "sm";

export interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: styles.primary,
  secondary: styles.secondary,
  ghost: styles.ghost,
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  md: styles.sizeMd,
  sm: styles.sizeSm,
};

/**
 * Design-system Button wrapping the Base UI headless Button primitive.
 *
 * The component is token-driven only: geometry, radii, focus treatment, and
 * color roles come from --app-* and --md-sys-* tokens; no ad hoc values. It
 * renders the Base UI Button (a <button>) so behavior, disabled handling, and
 * the focus ring stay consistent with the rest of the system.
 */
export function Button({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...rest
}: ButtonProps) {
  const composed = [styles.button, VARIANT_CLASS[variant], SIZE_CLASS[size], className]
    .filter(Boolean)
    .join(" ");

  return <BaseButton type={type} className={composed} {...rest} />;
}

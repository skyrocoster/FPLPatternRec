import { Form as BaseForm } from "@base-ui/react/form";
import type { FormProps as BaseFormProps } from "@base-ui/react/form";

import styles from "./AdvancedFormControls.module.css";

export type FormLayout = "stacked" | "inline" | "plain";

export type FormProps<FormValues extends Record<string, unknown> = Record<string, unknown>> = Omit<
  BaseFormProps<FormValues>,
  "className"
> & {
  className?: string;
  layout?: FormLayout;
};

/** Base UI form with project layout defaults and consolidated validation support. */
export function Form<FormValues extends Record<string, unknown> = Record<string, unknown>>({
  layout = "stacked",
  className,
  ...rest
}: FormProps<FormValues>) {
  return (
    <BaseForm<FormValues>
      {...rest}
      className={[styles.form, className].filter(Boolean).join(" ")}
      data-layout={layout}
    />
  );
}

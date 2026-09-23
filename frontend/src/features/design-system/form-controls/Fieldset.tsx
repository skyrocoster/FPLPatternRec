import { Fieldset as BaseFieldset } from "@base-ui/react/fieldset";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./AdvancedFormControls.module.css";

export interface FieldsetProps extends ComponentPropsWithoutRef<"fieldset"> {
  legend: ReactNode;
  description?: ReactNode;
}

/** Token-styled fieldset for grouping related form controls. */
export function Fieldset({ legend, description, className, children, ...rest }: FieldsetProps) {
  return (
    <BaseFieldset.Root {...rest} className={[styles.fieldset, className].filter(Boolean).join(" ")}>
      <BaseFieldset.Legend className={styles.legend}>{legend}</BaseFieldset.Legend>
      {description ? <p className={styles.description}>{description}</p> : null}
      {children}
    </BaseFieldset.Root>
  );
}

import type { ReactNode } from "react";

import styles from "./FormControls.module.css";

export interface DropdownOptionContentProps {
  leading?: ReactNode;
  primary: ReactNode;
  secondary?: ReactNode;
  trailing?: ReactNode;
}

/** Public visual anatomy for rich options. Option behavior remains control-owned. */
export function DropdownOptionContent({
  leading,
  primary,
  secondary,
  trailing,
}: DropdownOptionContentProps) {
  return (
    <span className={styles.optionAnatomy}>
      {leading ? <span className={styles.optionLeading}>{leading}</span> : null}
      <span className={styles.optionCopy}>
        <span className={styles.optionPrimary}>{primary}</span>
        {secondary ? <span className={styles.optionSecondary}>{secondary}</span> : null}
      </span>
      {trailing ? <span className={styles.optionTrailing}>{trailing}</span> : null}
    </span>
  );
}

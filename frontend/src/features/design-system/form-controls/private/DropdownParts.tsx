import type { ReactNode } from "react";

import type { DropdownOptionContentProps } from "../DropdownOptionContent";
import { DropdownOptionContent } from "../DropdownOptionContent";
import styles from "../FormControls.module.css";

export interface DropdownOptionDefinition {
  value: string;
  /** Required accessible name and default filtering/typeahead text. */
  label: string;
  disabled?: boolean;
  content?: Omit<DropdownOptionContentProps, "primary"> & { primary?: ReactNode };
  /** Replaces only the visual body; the owning control keeps option semantics and indicator. */
  customBody?: ReactNode;
}

export function DropdownItemBody({
  option,
  indicator,
}: {
  option: DropdownOptionDefinition;
  indicator?: ReactNode;
}) {
  return (
    <>
      <span className={styles.optionBody}>
        {option.customBody ?? (
          <DropdownOptionContent
            leading={option.content?.leading}
            primary={option.content?.primary ?? option.label}
            secondary={option.content?.secondary}
            trailing={option.content?.trailing}
          />
        )}
      </span>
      <span className={styles.optionIndicator} aria-hidden="true">
        {indicator ?? "✓"}
      </span>
    </>
  );
}

export function DropdownMessage({ children }: { children: ReactNode }) {
  return <span className={styles.dropdownMessage}>{children}</span>;
}

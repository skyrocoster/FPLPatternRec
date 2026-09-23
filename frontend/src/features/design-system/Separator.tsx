import { Separator as BaseSeparator } from "@base-ui/react/separator";
import type { ComponentPropsWithoutRef } from "react";

import styles from "./ContentPrimitives.module.css";

export interface SeparatorProps extends ComponentPropsWithoutRef<"div"> {
  orientation?: "horizontal" | "vertical";
}

/** Accessible visual separator for horizontal or vertical layouts. */
export function Separator({ orientation = "horizontal", className, ...rest }: SeparatorProps) {
  return (
    <BaseSeparator
      {...rest}
      orientation={orientation}
      className={[styles.separator, className].filter(Boolean).join(" ")}
    />
  );
}

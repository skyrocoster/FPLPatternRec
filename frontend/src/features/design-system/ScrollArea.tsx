import { ScrollArea as BaseScrollArea } from "@base-ui/react/scroll-area";
import type { ComponentPropsWithoutRef } from "react";

import styles from "./ContentPrimitives.module.css";

export type ScrollAreaOrientation = "vertical" | "horizontal" | "both";

export interface ScrollAreaProps extends ComponentPropsWithoutRef<"div"> {
  orientation?: ScrollAreaOrientation;
  viewportClassName?: string;
  contentClassName?: string;
  scrollbarClassName?: string;
}

/** Native scrolling viewport with optional token-styled Base UI scrollbars. */
export function ScrollArea({
  orientation = "vertical",
  viewportClassName,
  contentClassName,
  scrollbarClassName,
  className,
  children,
  ...rest
}: ScrollAreaProps) {
  const scrollbarClasses = [styles.scrollbar, scrollbarClassName].filter(Boolean).join(" ");

  return (
    <BaseScrollArea.Root
      {...rest}
      className={[styles.scrollArea, className].filter(Boolean).join(" ")}
    >
      <BaseScrollArea.Viewport
        className={[styles.scrollViewport, viewportClassName].filter(Boolean).join(" ")}
      >
        <BaseScrollArea.Content
          className={[styles.scrollContent, contentClassName].filter(Boolean).join(" ")}
        >
          {children}
        </BaseScrollArea.Content>
      </BaseScrollArea.Viewport>
      {orientation !== "horizontal" ? (
        <BaseScrollArea.Scrollbar className={scrollbarClasses} orientation="vertical">
          <BaseScrollArea.Thumb className={styles.scrollThumb} />
        </BaseScrollArea.Scrollbar>
      ) : null}
      {orientation !== "vertical" ? (
        <BaseScrollArea.Scrollbar className={scrollbarClasses} orientation="horizontal">
          <BaseScrollArea.Thumb className={styles.scrollThumb} />
        </BaseScrollArea.Scrollbar>
      ) : null}
      {orientation === "both" ? <BaseScrollArea.Corner className={styles.scrollCorner} /> : null}
    </BaseScrollArea.Root>
  );
}

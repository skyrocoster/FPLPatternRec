import { PreviewCard as BasePreviewCard } from "@base-ui/react/preview-card";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./OverlayPrimitives.module.css";

export interface PreviewCardProps extends Omit<
  ComponentPropsWithoutRef<"a">,
  "children" | "onChange"
> {
  trigger: ReactNode;
  children: ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  delay?: number;
  closeDelay?: number;
  popupClassName?: string;
}

/** Link preview that does not interrupt keyboard or screen-reader navigation. */
export function PreviewCard({
  trigger,
  children,
  open,
  defaultOpen,
  onOpenChange,
  delay,
  closeDelay,
  popupClassName,
  className,
  ...triggerProps
}: PreviewCardProps) {
  return (
    <BasePreviewCard.Root
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={(nextOpen) => onOpenChange?.(nextOpen)}
    >
      <BasePreviewCard.Trigger
        {...triggerProps}
        delay={delay}
        closeDelay={closeDelay}
        className={[styles.previewTrigger, className].filter(Boolean).join(" ")}
      >
        {trigger}
      </BasePreviewCard.Trigger>
      <BasePreviewCard.Portal>
        <BasePreviewCard.Positioner className={styles.positioner} sideOffset={8}>
          <BasePreviewCard.Popup
            className={[styles.previewPopup, popupClassName].filter(Boolean).join(" ")}
          >
            <BasePreviewCard.Arrow className={styles.arrow} />
            {children}
          </BasePreviewCard.Popup>
        </BasePreviewCard.Positioner>
      </BasePreviewCard.Portal>
    </BasePreviewCard.Root>
  );
}

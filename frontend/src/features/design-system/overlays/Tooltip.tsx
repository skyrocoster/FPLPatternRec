import { Tooltip as BaseTooltip } from "@base-ui/react/tooltip";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./OverlayPrimitives.module.css";

export interface TooltipProviderProps {
  children: ReactNode;
  delay?: number;
  closeDelay?: number;
  timeout?: number;
}

export interface TooltipProps {
  trigger: ReactNode;
  content: ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  disabled?: boolean;
  delay?: number;
  closeDelay?: number;
  closeOnClick?: boolean;
  triggerProps?: Omit<ComponentPropsWithoutRef<"button">, "children">;
  popupClassName?: string;
}

/** Shares hover-delay behavior between nearby tooltips. */
export function TooltipProvider(props: TooltipProviderProps) {
  return <BaseTooltip.Provider {...props} />;
}

/** Sighted-user hint attached to a focusable trigger. */
export function Tooltip({
  trigger,
  content,
  open,
  defaultOpen,
  onOpenChange,
  disabled,
  delay,
  closeDelay,
  closeOnClick,
  triggerProps,
  popupClassName,
}: TooltipProps) {
  return (
    <BaseTooltip.Root
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={(nextOpen) => onOpenChange?.(nextOpen)}
      disabled={disabled}
    >
      <BaseTooltip.Trigger
        {...triggerProps}
        delay={delay}
        closeDelay={closeDelay}
        closeOnClick={closeOnClick}
        className={[styles.tooltipTrigger, triggerProps?.className].filter(Boolean).join(" ")}
      >
        {trigger}
      </BaseTooltip.Trigger>
      <BaseTooltip.Portal>
        <BaseTooltip.Positioner className={styles.positioner} sideOffset={8}>
          <BaseTooltip.Popup
            className={[styles.tooltipPopup, popupClassName].filter(Boolean).join(" ")}
            role="tooltip"
          >
            <BaseTooltip.Arrow className={styles.arrow} />
            {content}
          </BaseTooltip.Popup>
        </BaseTooltip.Positioner>
      </BaseTooltip.Portal>
    </BaseTooltip.Root>
  );
}

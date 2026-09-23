import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./OverlayPrimitives.module.css";

export interface DialogProps {
  trigger?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  closeLabel?: ReactNode | null;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  modal?: boolean | "trap-focus";
  disablePointerDismissal?: boolean;
  triggerProps?: Omit<ComponentPropsWithoutRef<"button">, "children">;
  popupClassName?: string;
}

export type DialogCloseProps = ComponentPropsWithoutRef<"button">;

/** Close control that can be placed in custom Dialog footer content. */
export function DialogClose({ className, type = "button", ...rest }: DialogCloseProps) {
  return (
    <BaseDialog.Close
      {...rest}
      type={type}
      className={[styles.dialogClose, className].filter(Boolean).join(" ")}
    />
  );
}

/** Modal or non-modal dialog with project-standard surface and focus behavior. */
export function Dialog({
  trigger,
  title,
  description,
  children,
  footer,
  closeLabel = "Close",
  open,
  defaultOpen,
  onOpenChange,
  modal,
  disablePointerDismissal,
  triggerProps,
  popupClassName,
}: DialogProps) {
  return (
    <BaseDialog.Root
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={(nextOpen) => onOpenChange?.(nextOpen)}
      modal={modal}
      disablePointerDismissal={disablePointerDismissal}
    >
      {trigger ? (
        <BaseDialog.Trigger
          {...triggerProps}
          className={[styles.trigger, triggerProps?.className].filter(Boolean).join(" ")}
        >
          {trigger}
        </BaseDialog.Trigger>
      ) : null}
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className={styles.backdrop} />
        <BaseDialog.Viewport className={styles.dialogViewport}>
          <BaseDialog.Popup
            className={[styles.dialogPopup, popupClassName].filter(Boolean).join(" ")}
          >
            <BaseDialog.Title className={styles.dialogTitle}>{title}</BaseDialog.Title>
            {description ? (
              <BaseDialog.Description className={styles.dialogDescription}>
                {description}
              </BaseDialog.Description>
            ) : null}
            <div className={styles.dialogContent}>{children}</div>
            {footer || closeLabel ? (
              <div className={styles.dialogFooter}>
                {footer}
                {closeLabel ? <DialogClose>{closeLabel}</DialogClose> : null}
              </div>
            ) : null}
          </BaseDialog.Popup>
        </BaseDialog.Viewport>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}

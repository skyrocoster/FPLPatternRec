import { Menu as BaseMenu } from "@base-ui/react/menu";
import type { MenuPositionerProps } from "@base-ui/react/menu";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./MenuPrimitives.module.css";
import { MenuItemContent } from "./MenuItemContent";
import type { MenuItemDefinition } from "./menuTypes";

export interface MenuProps {
  trigger: ReactNode;
  items: readonly MenuItemDefinition[];
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  disabled?: boolean;
  modal?: boolean;
  loopFocus?: boolean;
  triggerClassName?: string;
  popupClassName?: string;
  triggerProps?: Omit<ComponentPropsWithoutRef<"button">, "children">;
  positionerProps?: Omit<MenuPositionerProps, "className">;
}

/** Button-triggered action or navigation menu. */
export function Menu({
  trigger,
  items,
  open,
  defaultOpen,
  onOpenChange,
  disabled,
  modal,
  loopFocus,
  triggerClassName,
  popupClassName,
  triggerProps,
  positionerProps,
}: MenuProps) {
  return (
    <BaseMenu.Root
      open={open}
      defaultOpen={defaultOpen}
      onOpenChange={(nextOpen) => onOpenChange?.(nextOpen)}
      disabled={disabled}
      modal={modal}
      loopFocus={loopFocus}
    >
      <BaseMenu.Trigger
        {...triggerProps}
        className={[styles.trigger, triggerClassName, triggerProps?.className]
          .filter(Boolean)
          .join(" ")}
      >
        {trigger}
      </BaseMenu.Trigger>
      <BaseMenu.Portal>
        <BaseMenu.Positioner sideOffset={4} {...positionerProps} className={styles.positioner}>
          <BaseMenu.Popup className={[styles.popup, popupClassName].filter(Boolean).join(" ")}>
            {items.map((item) => {
              if ("separator" in item) {
                return <BaseMenu.Separator className={styles.separator} key={item.id} />;
              }
              if (item.href) {
                return (
                  <BaseMenu.LinkItem
                    className={styles.item}
                    href={item.href}
                    target={item.target}
                    label={item.textValue}
                    closeOnClick={item.closeOnSelect}
                    key={item.id}
                  >
                    <MenuItemContent item={item} />
                  </BaseMenu.LinkItem>
                );
              }
              return (
                <BaseMenu.Item
                  className={styles.item}
                  disabled={item.disabled}
                  label={item.textValue}
                  closeOnClick={item.closeOnSelect}
                  onClick={() => item.onSelect?.()}
                  key={item.id}
                >
                  <MenuItemContent item={item} />
                </BaseMenu.Item>
              );
            })}
          </BaseMenu.Popup>
        </BaseMenu.Positioner>
      </BaseMenu.Portal>
    </BaseMenu.Root>
  );
}

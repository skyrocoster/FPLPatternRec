import { Menubar as BaseMenubar } from "@base-ui/react/menubar";
import type { ComponentPropsWithoutRef } from "react";

import { Menu } from "./Menu";
import styles from "./MenuPrimitives.module.css";
import type { MenubarDefinition } from "./menuTypes";

export interface MenubarProps extends ComponentPropsWithoutRef<"div"> {
  menus: readonly MenubarDefinition[];
  disabled?: boolean;
  modal?: boolean;
  orientation?: "horizontal" | "vertical";
  loopFocus?: boolean;
}

/** Keyboard-navigable application menubar composed from reusable Menu definitions. */
export function Menubar({
  menus,
  disabled,
  modal,
  orientation = "horizontal",
  loopFocus,
  className,
  ...rest
}: MenubarProps) {
  return (
    <BaseMenubar
      {...rest}
      className={[styles.menubar, className].filter(Boolean).join(" ")}
      disabled={disabled}
      modal={modal}
      orientation={orientation}
      loopFocus={loopFocus}
    >
      {menus.map((menu) => (
        <Menu
          key={menu.id}
          trigger={menu.label}
          items={menu.items}
          disabled={menu.disabled}
          triggerClassName={styles.menubarTrigger}
          positionerProps={{ sideOffset: 4 }}
        />
      ))}
    </BaseMenubar>
  );
}

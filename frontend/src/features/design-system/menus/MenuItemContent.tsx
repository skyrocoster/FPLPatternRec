import styles from "./MenuPrimitives.module.css";
import type { MenuItemDefinition } from "./menuTypes";

type RenderableMenuItem = Exclude<MenuItemDefinition, { separator: true }>;

/** Shared visual content for action and link items across menu variants. */
export function MenuItemContent({ item }: { item: RenderableMenuItem }) {
  return (
    <>
      {item.icon ? <span className={styles.itemIcon}>{item.icon}</span> : <span />}
      <span className={styles.itemLabel}>{item.label}</span>
      {item.shortcut ? <span className={styles.shortcut}>{item.shortcut}</span> : null}
    </>
  );
}

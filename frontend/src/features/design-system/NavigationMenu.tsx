import { NavigationMenu as BaseNavigationMenu } from "@base-ui/react/navigation-menu";
import { ChevronDown } from "lucide-react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./NavigationMenu.module.css";

export interface NavigationMenuLinkDefinition {
  id: string;
  label: ReactNode;
  href: string;
  description?: ReactNode;
  target?: string;
}

export interface NavigationMenuGroupDefinition {
  id: string;
  label: ReactNode;
  links: readonly NavigationMenuLinkDefinition[];
  disabled?: boolean;
}

export interface NavigationMenuDirectLinkDefinition extends NavigationMenuLinkDefinition {
  links?: never;
}

export type NavigationMenuItemDefinition =
  NavigationMenuGroupDefinition | NavigationMenuDirectLinkDefinition;

export interface NavigationMenuProps extends Omit<
  ComponentPropsWithoutRef<"nav">,
  "defaultValue" | "onChange"
> {
  items: readonly NavigationMenuItemDefinition[];
  value?: string | null;
  defaultValue?: string | null;
  onValueChange?: (value: string | null) => void;
  orientation?: "horizontal" | "vertical";
  delay?: number;
  closeDelay?: number;
}

function isGroup(item: NavigationMenuItemDefinition): item is NavigationMenuGroupDefinition {
  return "links" in item && Array.isArray(item.links);
}

/** Responsive top-level navigation with optional link panels. */
export function NavigationMenu({
  items,
  value,
  defaultValue,
  onValueChange,
  orientation = "horizontal",
  delay,
  closeDelay,
  className,
  ...rest
}: NavigationMenuProps) {
  return (
    <BaseNavigationMenu.Root<string>
      {...rest}
      className={[styles.root, className].filter(Boolean).join(" ")}
      value={value}
      defaultValue={defaultValue}
      onValueChange={(nextValue) => onValueChange?.(nextValue)}
      orientation={orientation}
      delay={delay}
      closeDelay={closeDelay}
    >
      <BaseNavigationMenu.List className={styles.list}>
        {items.map((item) => (
          <BaseNavigationMenu.Item key={item.id} value={item.id}>
            {isGroup(item) ? (
              <>
                <BaseNavigationMenu.Trigger className={styles.trigger} disabled={item.disabled}>
                  {item.label}
                  <BaseNavigationMenu.Icon className={styles.icon}>
                    <ChevronDown aria-hidden="true" />
                  </BaseNavigationMenu.Icon>
                </BaseNavigationMenu.Trigger>
                <BaseNavigationMenu.Content className={styles.content}>
                  <ul className={styles.panelList}>
                    {item.links.map((link) => (
                      <li key={link.id}>
                        <BaseNavigationMenu.Link
                          className={styles.panelLink}
                          href={link.href}
                          target={link.target}
                        >
                          <span className={styles.linkLabel}>{link.label}</span>
                          {link.description ? (
                            <span className={styles.linkDescription}>{link.description}</span>
                          ) : null}
                        </BaseNavigationMenu.Link>
                      </li>
                    ))}
                  </ul>
                </BaseNavigationMenu.Content>
              </>
            ) : (
              <BaseNavigationMenu.Link
                className={styles.directLink}
                href={item.href}
                target={item.target}
              >
                {item.label}
              </BaseNavigationMenu.Link>
            )}
          </BaseNavigationMenu.Item>
        ))}
      </BaseNavigationMenu.List>
      <BaseNavigationMenu.Portal>
        <BaseNavigationMenu.Positioner className={styles.positioner} sideOffset={8}>
          <BaseNavigationMenu.Popup className={styles.popup}>
            <BaseNavigationMenu.Arrow className={styles.arrow} />
            <BaseNavigationMenu.Viewport className={styles.viewport} />
          </BaseNavigationMenu.Popup>
        </BaseNavigationMenu.Positioner>
      </BaseNavigationMenu.Portal>
    </BaseNavigationMenu.Root>
  );
}

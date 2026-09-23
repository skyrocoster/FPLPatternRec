import type { ReactNode } from "react";

export interface MenuActionItemDefinition {
  id: string;
  label: ReactNode;
  textValue?: string;
  icon?: ReactNode;
  shortcut?: ReactNode;
  disabled?: boolean;
  closeOnSelect?: boolean;
  onSelect?: () => void;
  href?: never;
  separator?: never;
}

export interface MenuLinkItemDefinition {
  id: string;
  label: ReactNode;
  textValue?: string;
  icon?: ReactNode;
  shortcut?: ReactNode;
  href: string;
  target?: string;
  closeOnSelect?: boolean;
  onSelect?: never;
  disabled?: never;
  separator?: never;
}

export interface MenuSeparatorDefinition {
  id: string;
  separator: true;
  label?: never;
  href?: never;
  onSelect?: never;
}

export type MenuItemDefinition =
  MenuActionItemDefinition | MenuLinkItemDefinition | MenuSeparatorDefinition;

export interface MenubarDefinition {
  id: string;
  label: ReactNode;
  items: readonly MenuItemDefinition[];
  disabled?: boolean;
}

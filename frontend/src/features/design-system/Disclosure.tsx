import { Collapsible } from "@base-ui/react/collapsible";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import styles from "./Disclosure.module.css";

export interface DisclosureProps extends ComponentPropsWithoutRef<"div"> {
  summary: ReactNode;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Design-system Disclosure wrapping the Base UI headless Collapsible primitive.
 *
 * The component is token-driven only: geometry, radii, focus treatment, and
 * color roles come from --app-* and --md-sys-* tokens; no ad hoc values. It
 * renders a Base UI Collapsible (Root -> Trigger button -> Panel div) so the
 * open/close state, ARIA wiring, and focus ring stay consistent across the
 * system. Pass `className` to vary placement, e.g. a mobile-only variant.
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  open,
  onOpenChange,
  className,
  ...rest
}: DisclosureProps) {
  const composed = [styles.disclosure, className].filter(Boolean).join(" ");

  return (
    <Collapsible.Root
      className={composed}
      defaultOpen={defaultOpen}
      open={open}
      onOpenChange={(nextOpen) => onOpenChange?.(nextOpen)}
      {...rest}
    >
      <Collapsible.Trigger className={styles.summary} type="button">
        {summary}
      </Collapsible.Trigger>
      <Collapsible.Panel className={styles.panel}>{children}</Collapsible.Panel>
    </Collapsible.Root>
  );
}

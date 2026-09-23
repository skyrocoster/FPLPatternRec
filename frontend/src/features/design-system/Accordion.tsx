import { Accordion as BaseAccordion } from "@base-ui/react/accordion";
import { ChevronDown } from "lucide-react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import styles from "./ContentPrimitives.module.css";

export interface AccordionItemDefinition {
  value: string;
  summary: ReactNode;
  content: ReactNode;
  disabled?: boolean;
  className?: string;
}

export interface AccordionProps extends Omit<
  ComponentPropsWithoutRef<"div">,
  "defaultValue" | "onChange"
> {
  items: readonly AccordionItemDefinition[];
  value?: string[];
  defaultValue?: string[];
  onValueChange?: (value: string[]) => void;
  multiple?: boolean;
  disabled?: boolean;
  keepMounted?: boolean;
  hiddenUntilFound?: boolean;
  itemClassName?: string;
  contentClassName?: string;
}

/** Reusable token-styled accordion with consumer-owned summaries and panel content. */
export function Accordion({
  items,
  value,
  defaultValue,
  onValueChange,
  multiple,
  disabled,
  keepMounted,
  hiddenUntilFound,
  itemClassName,
  contentClassName,
  className,
  ...rest
}: AccordionProps) {
  return (
    <BaseAccordion.Root
      {...rest}
      className={[styles.accordion, className].filter(Boolean).join(" ")}
      value={value}
      defaultValue={defaultValue}
      onValueChange={(nextValue) => onValueChange?.(nextValue)}
      multiple={multiple}
      disabled={disabled}
      keepMounted={keepMounted}
      hiddenUntilFound={hiddenUntilFound}
    >
      {items.map((item) => (
        <BaseAccordion.Item
          key={item.value}
          value={item.value}
          disabled={item.disabled}
          className={[styles.accordionItem, itemClassName, item.className]
            .filter(Boolean)
            .join(" ")}
        >
          <BaseAccordion.Header className={styles.accordionHeader}>
            <BaseAccordion.Trigger className={styles.accordionTrigger}>
              <span>{item.summary}</span>
              <ChevronDown className={styles.accordionIcon} aria-hidden="true" />
            </BaseAccordion.Trigger>
          </BaseAccordion.Header>
          <BaseAccordion.Panel className={styles.accordionPanel}>
            <div className={[styles.accordionContent, contentClassName].filter(Boolean).join(" ")}>
              {item.content}
            </div>
          </BaseAccordion.Panel>
        </BaseAccordion.Item>
      ))}
    </BaseAccordion.Root>
  );
}

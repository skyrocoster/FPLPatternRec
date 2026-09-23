import { Select as BaseSelect } from "@base-ui/react/select";
import { ChevronDown } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import styles from "./FormControls.module.css";
import {
  DropdownItemBody,
  DropdownMessage,
  type DropdownOptionDefinition,
} from "./private/DropdownParts";
import { dropdownPositionerProps } from "./private/dropdownPositionerProps";

export interface SelectProps {
  options: readonly DropdownOptionDefinition[];
  value: string | null;
  onValueChange: (value: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
  loading?: boolean;
  loadingContent?: ReactNode;
  emptyContent?: ReactNode;
  ariaLabel?: string;
  preferredPopupWidth?: string;
}

export function Select({
  options,
  value,
  onValueChange,
  placeholder = "Choose an option",
  disabled,
  readOnly,
  required,
  loading = false,
  loadingContent = "Loading…",
  emptyContent = "No options found.",
  ariaLabel,
  preferredPopupWidth,
}: SelectProps) {
  const visibleOptions = loading ? [] : options;
  return (
    <BaseSelect.Root
      modal={false}
      disabled={disabled}
      readOnly={readOnly}
      required={required}
      value={value}
      items={options.map((option) => ({ value: option.value, label: option.label }))}
      onValueChange={(next) => onValueChange(next)}
    >
      <BaseSelect.Trigger className={styles.selectTrigger} aria-label={ariaLabel}>
        <BaseSelect.Value placeholder={placeholder} />
        <BaseSelect.Icon className={styles.triggerIcon}>
          <ChevronDown aria-hidden="true" size={18} />
        </BaseSelect.Icon>
      </BaseSelect.Trigger>
      <BaseSelect.Portal>
        <BaseSelect.Positioner
          {...dropdownPositionerProps}
          className={styles.dropdownPositioner}
          style={{ "--preferred-popup-width": preferredPopupWidth } as CSSProperties}
        >
          <BaseSelect.Popup className={styles.dropdownPopup}>
            <BaseSelect.List className={styles.dropdownList}>
              {visibleOptions.map((option) => (
                <BaseSelect.Item
                  aria-label={option.label}
                  className={styles.dropdownItem}
                  disabled={option.disabled}
                  key={option.value}
                  label={option.label}
                  value={option.value}
                >
                  <DropdownItemBody
                    option={option}
                    indicator={<BaseSelect.ItemIndicator>✓</BaseSelect.ItemIndicator>}
                  />
                </BaseSelect.Item>
              ))}
            </BaseSelect.List>
            {visibleOptions.length === 0 ? (
              <DropdownMessage>{loading ? loadingContent : emptyContent}</DropdownMessage>
            ) : null}
          </BaseSelect.Popup>
        </BaseSelect.Positioner>
      </BaseSelect.Portal>
    </BaseSelect.Root>
  );
}

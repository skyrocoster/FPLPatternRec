import { Popover } from "@base-ui/react/popover";
import { DayPicker, type ClassNames } from "react-day-picker";
import { useRef, useState } from "react";

import styles from "./CalendarDate.module.css";
import {
  formatUtcDate,
  getUtcCalendarDay,
  isFutureUtcDate,
  normalizeToUtcMidnight,
  toUtcMidnight,
} from "./CalendarDateUtils";

export type CalendarDateValue = Date | null;

export interface CalendarDateProps {
  value: CalendarDateValue;
  onChange: (value: CalendarDateValue) => void;
  label?: string;
  /** Marks the trigger as invalid without owning form-level error text. */
  invalid?: boolean;
  /** Links the trigger to external descriptive or error text. */
  describedBy?: string;
  /** Stable id for the trigger so external labels or errors can reference it. */
  triggerId?: string;
}

const calendarClassNames = {
  root: styles.calendarRoot,
  chevron: styles.chevron,
  day: styles.day,
  day_button: styles.dayButton,
  caption_label: styles.captionLabel,
  dropdowns: styles.dropdowns,
  dropdown: styles.dropdown,
  dropdown_root: styles.dropdownRoot,
  month_grid: styles.monthGrid,
  month_caption: styles.monthCaption,
  month: styles.month,
  months: styles.months,
  nav: styles.nav,
  button_next: styles.navButton,
  button_previous: styles.navButton,
  week: styles.week,
  weeks: styles.weeks,
  weekday: styles.weekday,
  weekdays: styles.weekdays,
  disabled: styles.disabled,
  focused: styles.focused,
  outside: styles.outside,
  selected: styles.selected,
  today: styles.today,
} satisfies Partial<ClassNames>;

export function CalendarDate({
  value,
  onChange,
  label = "Date",
  invalid = false,
  describedBy,
  triggerId,
}: CalendarDateProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const now = new Date();
  const today = toUtcMidnight(getUtcCalendarDay(now));
  const selected = value ? normalizeToUtcMidnight(value) : undefined;
  const displayValue = value ? formatUtcDate(value) : "Choose date";
  const accessibleLabel = `${label}: ${displayValue}`;

  const handleSelect = (date: Date | undefined) => {
    onChange(date ? normalizeToUtcMidnight(date) : null);
    setOpen(false);
  };

  const clearDate = () => {
    onChange(null);
    setOpen(false);
  };

  return (
    <Popover.Root open={open} modal onOpenChange={setOpen}>
      <Popover.Trigger
        ref={triggerRef}
        id={triggerId}
        className={styles.trigger}
        aria-label={accessibleLabel}
        aria-invalid={invalid ? true : undefined}
        aria-describedby={describedBy}
      >
        <span aria-hidden="true">{displayValue}</span>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Backdrop className={styles.backdrop} />
        <Popover.Positioner
          className={styles.positioner}
          side="bottom"
          align="start"
          sideOffset={8}
        >
          <Popover.Popup
            className={styles.popup}
            initialFocus
            finalFocus={triggerRef}
            data-testid="calendar-date-popup"
          >
            <Popover.Title className={styles.title}>{label}</Popover.Title>
            <Popover.Description className={styles.description}>Select a date.</Popover.Description>
            <DayPicker
              mode="single"
              selected={selected}
              onSelect={handleSelect}
              defaultMonth={selected ?? today}
              today={today}
              endMonth={today}
              disabled={(date) => isFutureUtcDate(date, now)}
              timeZone="UTC"
              aria-label={`${label} calendar`}
              classNames={calendarClassNames}
            />
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.clearButton}
                disabled={!value}
                onClick={clearDate}
              >
                Clear date
              </button>
              <Popover.Close className={styles.closeButton} aria-label="Close calendar">
                Close
              </Popover.Close>
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

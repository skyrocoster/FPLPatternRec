export interface UtcCalendarDay {
  year: number;
  month: number;
  day: number;
}

/** Return the calendar-day parts of an instant without consulting local time. */
export function getUtcCalendarDay(instant: Date): UtcCalendarDay {
  if (Number.isNaN(instant.getTime())) {
    throw new RangeError("Calendar date must be valid");
  }
  return {
    year: instant.getUTCFullYear(),
    month: instant.getUTCMonth(),
    day: instant.getUTCDate(),
  };
}

/** Create the canonical HTTP value for one UTC calendar day. */
export function toUtcMidnight(day: UtcCalendarDay): Date {
  return new Date(Date.UTC(day.year, day.month, day.day, 0, 0, 0, 0));
}

export function normalizeToUtcMidnight(instant: Date): Date {
  return toUtcMidnight(getUtcCalendarDay(instant));
}

/** Compare calendar tuples so a late current-day instant is never treated as future. */
export function isFutureUtcDate(candidate: Date, now: Date): boolean {
  const candidateDay = getUtcCalendarDay(candidate);
  const currentDay = getUtcCalendarDay(now);
  if (candidateDay.year !== currentDay.year) return candidateDay.year > currentDay.year;
  if (candidateDay.month !== currentDay.month) return candidateDay.month > currentDay.month;
  return candidateDay.day > currentDay.day;
}

export function formatUtcDate(value: Date): string {
  const { year, month, day } = getUtcCalendarDay(value);
  return `${String(year).padStart(4, "0")}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

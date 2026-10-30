import dayjs from "dayjs";

// Display formats from the Figma design.
const DATE_FORMAT = "DD-MM-YYYY";
const TIME_FORMAT = "h:mm A";

export function formatDate(value: string): string {
  return dayjs(value).format(DATE_FORMAT);
}

export function formatTime(value: string): string {
  return dayjs(value).format(TIME_FORMAT);
}

/** "31-10-2026, 9:00 AM" */
export function formatDateTime(value: string): string {
  return `${formatDate(value)}, ${formatTime(value)}`;
}

const INDIA_PREFIX = "+91";

/** E.164 for display: Indian numbers as "+91 9876543210", others unchanged. */
export function formatPhone(e164: string): string {
  return e164.startsWith(INDIA_PREFIX) ? `${INDIA_PREFIX} ${e164.slice(INDIA_PREFIX.length)}` : e164;
}

/** "1 Recipient", "5 Recipients". */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

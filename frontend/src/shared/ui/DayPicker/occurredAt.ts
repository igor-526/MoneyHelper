import dayjs, { type Dayjs } from "dayjs";

/**
 * Момент операции по выбранной дате: время суток берётся текущее, а у редактируемой операции с неизменённой датой
 * сохраняется исходный момент.
 */
export function toOccurredAt(day: Dayjs, original?: string): string {
  if (original !== undefined && dayjs(original).isSame(day, "day")) return original;
  const now = dayjs();
  return toLocalDateTime(day.hour(now.hour()).minute(now.minute()).second(now.second()));
}

export function toLocalDateTime(value: Dayjs): string {
  return value.format("YYYY-MM-DDTHH:mm:ss");
}

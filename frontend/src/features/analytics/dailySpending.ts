import dayjs, { type Dayjs } from "dayjs";
import type { AnalyticsBucket, AnalyticsRange } from "./Analytics";
import { sumAmounts } from "./sumAmounts";

export interface DailySpending {
  /** Календарный день `YYYY-MM-DD`. */
  day: string;
  amount: string;
}

const DAY_FORMAT = "YYYY-MM-DD";

/**
 * Расходы по дням без пропусков: дни без трат получают `0`. Границы — заданный диапазон, а без него (весь период) —
 * первый и последний день с тратами.
 */
export function buildDailySpending(
  buckets: AnalyticsBucket[],
  range: AnalyticsRange,
): DailySpending[] {
  const amountByDay = new Map(buckets.map((bucket) => [bucket.group_key, bucket.expense]));
  const days = [...amountByDay.keys()].sort();
  const first = range.dateFrom ? dayjs(range.dateFrom) : days[0] ? dayjs(days[0]) : undefined;
  const last = range.dateTo ? dayjs(range.dateTo) : days.at(-1) ? dayjs(days.at(-1)) : undefined;
  if (first === undefined || last === undefined) return [];

  const series: DailySpending[] = [];
  for (let day: Dayjs = first.startOf("day"); !day.isAfter(last); day = day.add(1, "day")) {
    const key = day.format(DAY_FORMAT);
    series.push({ day: key, amount: amountByDay.get(key) ?? "0" });
  }
  return series;
}

export function totalSpending(series: DailySpending[]): string {
  return sumAmounts(series.map((point) => point.amount));
}

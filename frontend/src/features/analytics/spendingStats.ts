import type { DailySpending } from "./dailySpending";

export interface SpendingStat {
  label: "Минимум" | "Максимум" | "Средняя" | "Медиана";
  value: string;
}

function scaleOf(value: string): number {
  return (value.split(".")[1] ?? "").length;
}

function unitsOf(value: string, scale: number): bigint {
  const [integer = "0", fraction = ""] = value.split(".");
  return BigInt(integer + fraction.padEnd(scale, "0"));
}

function amountOf(units: bigint, scale: number): string {
  const digits = units.toString().padStart(scale + 1, "0");
  return scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
}

function divideRounded(units: bigint, divisor: bigint): bigint {
  return (units + divisor / 2n) / divisor;
}

export function spendingStats(series: DailySpending[]): SpendingStat[] {
  if (series.length === 0) return [];
  const scale = Math.max(...series.map((item) => scaleOf(item.amount)));
  const values = series
    .map((item) => unitsOf(item.amount, scale))
    .sort((left, right) => (left < right ? -1 : 1));
  const total = values.reduce((sum, value) => sum + value, 0n);
  const middle = Math.floor(values.length / 2);
  const median =
    values.length % 2 === 0
      ? divideRounded(values[middle - 1]! + values[middle]!, 2n)
      : values[middle]!;
  return [
    { label: "Минимум", value: amountOf(values[0]!, scale) },
    { label: "Максимум", value: amountOf(values.at(-1)!, scale) },
    { label: "Средняя", value: amountOf(divideRounded(total, BigInt(values.length)), scale) },
    { label: "Медиана", value: amountOf(median, scale) },
  ];
}

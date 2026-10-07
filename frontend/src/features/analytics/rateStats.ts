import type { ExchangeRatePoint } from "./Analytics";

const RATE_SCALE = 10;
const RATE_FACTOR = 10n ** BigInt(RATE_SCALE);

export interface RateStat {
  label: "Минимум" | "Максимум" | "Средняя";
  value: string;
}

function unitsOf(value: string): bigint {
  const [integer = "0", fraction = ""] = value.split(".");
  return (
    BigInt(integer) * RATE_FACTOR + BigInt(fraction.padEnd(RATE_SCALE, "0").slice(0, RATE_SCALE))
  );
}

function rateOf(units: bigint): string {
  const integer = units / RATE_FACTOR;
  const fraction = (units % RATE_FACTOR).toString().padStart(RATE_SCALE, "0");
  return `${integer}.${fraction}`;
}

function divideRounded(units: bigint, divisor: bigint): bigint {
  return (units + divisor / 2n) / divisor;
}

export function rateStats(points: ExchangeRatePoint[]): RateStat[] {
  if (points.length === 0) return [];
  const values = points
    .map((point) => unitsOf(point.rate))
    .sort((left, right) => (left < right ? -1 : 1));
  const total = values.reduce((sum, value) => sum + value, 0n);
  return [
    { label: "Минимум", value: rateOf(values[0]!) },
    { label: "Максимум", value: rateOf(values.at(-1)!) },
    { label: "Средняя", value: rateOf(divideRounded(total, BigInt(values.length))) },
  ];
}

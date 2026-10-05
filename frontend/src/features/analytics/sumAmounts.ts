/** Точная сумма десятичных строк без `float`: целые в `BigInt`, масштаб — максимальное число знаков слагаемых. */
export function sumAmounts(values: string[]): string {
  const scale = Math.max(0, ...values.map((value) => (value.split(".")[1] ?? "").length));
  const total = values.reduce((sum, value) => {
    const negative = value.startsWith("-");
    const [integer = "0", fraction = ""] = value.replace("-", "").split(".");
    const units = BigInt(integer + fraction.padEnd(scale, "0"));
    return negative ? sum - units : sum + units;
  }, 0n);
  const sign = total < 0n ? "-" : "";
  const digits = (total < 0n ? -total : total).toString().padStart(scale + 1, "0");
  return scale === 0 ? sign + digits : `${sign}${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
}

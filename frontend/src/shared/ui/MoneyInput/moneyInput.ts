export function normalizeMoneyAmount(value: string): string | undefined {
  if (value.includes(".") && value.includes(",")) return undefined;
  return value.replace(",", ".");
}

/** Разрешены цифры и один десятичный разделитель; допускаются промежуточные состояния вроде "12,". */
export function isValidMoneyAmount(value: string, decimalPlaces?: number): boolean {
  const normalized = normalizeMoneyAmount(value);
  if (normalized === undefined) return false;
  const pattern =
    decimalPlaces == null ? /^\d*\.?\d*$/ : new RegExp(`^\\d*(\\.\\d{0,${decimalPlaces}})?$`);
  return pattern.test(normalized);
}

/**
 * Backend отдаёт суммы с 8 знаками (`NUMERIC(24, 8)`): убирает хвостовые нули дробной части, оставляя не меньше
 * `minFractionDigits` знаков (если они были). Сумма остаётся строкой, без приведения к `number`.
 */
export function formatAmount(amount: string, minFractionDigits = 2): string {
  const [integer = "", fraction] = amount.split(".");
  if (fraction === undefined) return amount;
  let end = fraction.length;
  while (end > minFractionDigits && fraction[end - 1] === "0") end -= 1;
  return end === 0 ? integer : `${integer}.${fraction.slice(0, end)}`;
}

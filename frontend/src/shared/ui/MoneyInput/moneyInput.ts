/** Разрешены цифры и не более одной десятичной точки; допускаются промежуточные состояния ввода вроде "12.". */
export function isValidMoneyAmount(value: string, decimalPlaces?: number): boolean {
  const pattern =
    decimalPlaces == null ? /^\d*\.?\d*$/ : new RegExp(`^\\d*(\\.\\d{0,${decimalPlaces}})?$`);
  return pattern.test(value);
}

import { Input } from "antd";
import type { ChangeEvent } from "react";
import { isValidMoneyAmount } from "./moneyInput";

export interface MoneyInputProps {
  value: string;
  onChange: (value: string) => void;
  decimalPlaces?: number;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}

/**
 * Контролируемый ввод денежной суммы: значение всегда строка, никогда не приводится к `number`.
 * `onChange(value: string)` совместим с `Form.Item` без дополнительных пропов (`getValueFromEvent` по умолчанию).
 */
export function MoneyInput({
  value,
  onChange,
  decimalPlaces,
  placeholder,
  disabled,
  id,
}: MoneyInputProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.value;
    if (isValidMoneyAmount(next, decimalPlaces)) {
      onChange(next);
    }
  };

  return (
    <Input
      id={id}
      value={value}
      onChange={handleChange}
      inputMode="decimal"
      autoComplete="off"
      placeholder={placeholder}
      disabled={disabled}
    />
  );
}

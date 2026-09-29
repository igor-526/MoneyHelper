import { Select } from "antd";
import { useCurrencies } from "./useCurrencies";

interface CurrencyPickerBaseProps {
  placeholder?: string;
  disabled?: boolean;
}

interface SingleCurrencyPickerProps extends CurrencyPickerBaseProps {
  multiple?: false;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}

interface MultipleCurrencyPickerProps extends CurrencyPickerBaseProps {
  multiple: true;
  value: string[];
  onChange: (value: string[]) => void;
}

export type CurrencyPickerProps = SingleCurrencyPickerProps | MultipleCurrencyPickerProps;

const UNAVAILABLE_PLACEHOLDER = "Валюты недоступны";

/** Выбор одной или нескольких валют из глобального справочника (`GET /api/currencies`). */
export function CurrencyPicker(props: CurrencyPickerProps) {
  const { data: currencies, isPending, isError } = useCurrencies();

  const options = (currencies ?? []).map((currency) => ({
    value: currency.id,
    label: `${currency.code} — ${currency.name}`,
  }));
  const placeholder = isError ? UNAVAILABLE_PLACEHOLDER : props.placeholder;

  if (props.multiple) {
    return (
      <Select
        mode="multiple"
        value={props.value}
        onChange={props.onChange}
        options={options}
        loading={isPending}
        disabled={props.disabled || isError}
        placeholder={placeholder}
      />
    );
  }

  return (
    <Select
      value={props.value}
      onChange={props.onChange}
      options={options}
      loading={isPending}
      disabled={props.disabled || isError}
      placeholder={placeholder}
      allowClear
    />
  );
}

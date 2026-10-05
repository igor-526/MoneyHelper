import { DatePicker } from "antd";
import dayjs, { type Dayjs } from "dayjs";

export interface DayPickerProps {
  value?: Dayjs | null;
  onChange?: (value: Dayjs | null) => void;
}

const PRESETS = [{ label: "Вчера", value: () => dayjs().subtract(1, "day") }];

/** Выбор только даты (без времени) с быстрой кнопкой «Вчера»; подходит как контрол `Form.Item`. */
export function DayPicker({ value, onChange }: DayPickerProps) {
  return (
    <DatePicker
      style={{ width: "100%" }}
      format="DD.MM.YYYY"
      presets={PRESETS}
      allowClear={false}
      value={value}
      onChange={onChange}
    />
  );
}

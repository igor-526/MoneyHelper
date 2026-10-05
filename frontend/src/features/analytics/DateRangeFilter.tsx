import { Button, DatePicker, Flex } from "antd";
import dayjs from "dayjs";
import { DATE_RANGE_PRESETS, type DateRange, findActivePreset } from "./dateRangePresets";

export interface DateRangeFilterProps {
  /** `null` — диапазон не задан: аналитика за весь период воркспейса. */
  value: DateRange | null;
  onChange: (value: DateRange | null) => void;
}

export function DateRangeFilter({ value, onChange }: DateRangeFilterProps) {
  const activeKey = findActivePreset(value, dayjs());

  return (
    <Flex vertical gap={8}>
      <DatePicker.RangePicker
        aria-label="Диапазон дат"
        placeholder={["Дата от", "Дата до"]}
        value={value}
        onChange={(dates) => onChange(dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null)}
        allowClear
      />
      <Flex gap={8} wrap>
        {DATE_RANGE_PRESETS.map((preset) => (
          <Button
            key={preset.key}
            type={preset.key === activeKey ? "primary" : "default"}
            onClick={() => onChange(preset.range(dayjs()))}
          >
            {preset.label}
          </Button>
        ))}
      </Flex>
    </Flex>
  );
}

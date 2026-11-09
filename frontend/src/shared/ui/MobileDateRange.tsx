import { DatePicker, Flex, Input } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useId } from "react";
import { useIsMobile } from "./useIsMobile";

interface Props {
  value: [Dayjs, Dayjs] | null;
  onChange: (value: [Dayjs, Dayjs] | null) => void;
}

export function MobileDateRange({ value, onChange }: Props) {
  const isMobile = useIsMobile();
  const id = useId();
  if (!isMobile) {
    return (
      <DatePicker.RangePicker
        aria-label="Диапазон дат"
        value={value}
        placeholder={["Дата от", "Дата до"]}
        onChange={(dates) => onChange(dates?.[0] && dates[1] ? [dates[0], dates[1]] : null)}
      />
    );
  }
  return (
    <Flex vertical gap={8}>
      <label htmlFor={`${id}-from`}>
        Дата от
        <Input
          id={`${id}-from`}
          type="date"
          aria-label="Дата от"
          style={{ minWidth: 0, width: "100%" }}
          value={value?.[0].format("YYYY-MM-DD") ?? ""}
          max={value?.[1].format("YYYY-MM-DD")}
          onChange={(event) => {
            const date = event.target.value;
            onChange(
              date
                ? [
                    dayjs(date),
                    value?.[1] && !value[1].isBefore(dayjs(date)) ? value[1] : dayjs(date),
                  ]
                : null,
            );
          }}
        />
      </label>
      <label htmlFor={`${id}-to`}>
        Дата до
        <Input
          id={`${id}-to`}
          type="date"
          aria-label="Дата до"
          style={{ minWidth: 0, width: "100%" }}
          value={value?.[1].format("YYYY-MM-DD") ?? ""}
          min={value?.[0].format("YYYY-MM-DD")}
          onChange={(event) => {
            const date = event.target.value;
            onChange(
              date
                ? [
                    value?.[0] && !value[0].isAfter(dayjs(date)) ? value[0] : dayjs(date),
                    dayjs(date),
                  ]
                : null,
            );
          }}
        />
      </label>
    </Flex>
  );
}

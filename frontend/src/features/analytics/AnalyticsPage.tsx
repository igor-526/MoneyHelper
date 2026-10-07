import { Flex, Segmented, Typography } from "antd";
import { useState } from "react";
import { ANALYTICS_MODES, DEFAULT_ANALYTICS_MODE } from "./analyticsModes";
import { type DateRange } from "./dateRangePresets";
import { DateRangeFilter } from "./DateRangeFilter";
import { toLocalDateTime } from "@/shared/ui";

export function AnalyticsPage() {
  const [modeKey, setModeKey] = useState(DEFAULT_ANALYTICS_MODE.key);
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const mode = ANALYTICS_MODES.find((item) => item.key === modeKey) ?? DEFAULT_ANALYTICS_MODE;

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Аналитика
      </Typography.Title>
      <Segmented
        aria-label="Режим"
        options={ANALYTICS_MODES.map((item) => ({ label: item.label, value: item.key }))}
        value={modeKey}
        onChange={setModeKey}
        block
      />
      <DateRangeFilter value={dateRange} onChange={setDateRange} />
      <Typography.Text type="secondary">
        {dateRange === null ? "Весь период" : "Выбранный период"}
      </Typography.Text>
      <mode.Panel
        range={{
          dateFrom: dateRange ? toLocalDateTime(dateRange[0].startOf("day")) : undefined,
          dateTo: dateRange ? toLocalDateTime(dateRange[1].endOf("day")) : undefined,
        }}
      />
    </Flex>
  );
}

import { Checkbox, Flex, Segmented, Typography } from "antd";
import { useState } from "react";
import { ANALYTICS_MODES, DEFAULT_ANALYTICS_MODE } from "./analyticsModes";
import { type DateRange } from "./dateRangePresets";
import { DateRangeFilter } from "./DateRangeFilter";
import { toLocalDateTime } from "@/shared/ui";

export function AnalyticsPage() {
  const [modeKey, setModeKey] = useState(DEFAULT_ANALYTICS_MODE.key);
  const [includeExcluded, setIncludeExcluded] = useState(false);
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
      <Checkbox
        style={{ minHeight: 44, alignItems: "center" }}
        checked={includeExcluded}
        onChange={(event) => setIncludeExcluded(event.target.checked)}
      >
        Включать операции «Не участвует в аналитике»
      </Checkbox>
      <Typography.Text type="secondary">
        {dateRange === null ? "Весь период" : "Выбранный период"}
      </Typography.Text>
      <mode.Panel
        range={{
          includeExcluded,
          dateFrom: dateRange ? toLocalDateTime(dateRange[0].startOf("day")) : undefined,
          dateTo: dateRange ? toLocalDateTime(dateRange[1].endOf("day")) : undefined,
        }}
      />
    </Flex>
  );
}

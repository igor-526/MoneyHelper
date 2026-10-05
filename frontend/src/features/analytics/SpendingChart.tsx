import dayjs from "dayjs";
import { theme } from "antd";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatAmount } from "@/shared/ui";
import type { DailySpending } from "./dailySpending";

export interface SpendingChartProps {
  series: DailySpending[];
  currencyCode: string;
}

const SHORT_DAY_FORMAT = "DD.MM";
const FULL_DAY_FORMAT = "DD.MM.YYYY";

/** Столбчатый график трат по дням. Цвета — из токенов antd. */
export function SpendingChart({ series, currencyCode }: SpendingChartProps) {
  const { token } = theme.useToken();
  const data = series.map((point) => ({ day: point.day, value: Number(point.amount) }));

  return (
    <div role="img" aria-label={`График трат по дням, ${currencyCode}`}>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={token.colorBorderSecondary} />
          <XAxis
            dataKey="day"
            tickFormatter={(day: string) => dayjs(day).format(SHORT_DAY_FORMAT)}
            tick={{ fill: token.colorTextSecondary }}
            stroke={token.colorBorder}
            minTickGap={16}
          />
          <YAxis
            width={56}
            tick={{ fill: token.colorTextSecondary }}
            stroke={token.colorBorder}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: token.colorFillSecondary }}
            labelFormatter={(day) => dayjs(String(day)).format(FULL_DAY_FORMAT)}
            formatter={(value) => [`${formatAmount(String(value))} ${currencyCode}`, "Траты"]}
            contentStyle={{
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadius,
              color: token.colorText,
            }}
            itemStyle={{ color: token.colorText }}
            labelStyle={{ color: token.colorText }}
          />
          <Bar dataKey="value" fill={token.blue} radius={[4, 4, 0, 0]} maxBarSize={32} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

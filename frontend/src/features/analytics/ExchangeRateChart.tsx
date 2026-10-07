import dayjs from "dayjs";
import { theme } from "antd";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ExchangeRatePoint } from "./Analytics";

export interface ExchangeRateChartProps {
  points: ExchangeRatePoint[];
  currencyCode: string;
}

export function ExchangeRateChart({ points, currencyCode }: ExchangeRateChartProps) {
  const { token } = theme.useToken();
  const data = points.map((point) => ({ ...point, value: Number(point.rate) }));

  return (
    <div role="img" aria-label={`График курса ${currencyCode} к RUB`}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={token.colorBorderSecondary} />
          <XAxis
            dataKey="date"
            tickFormatter={(value: string) => dayjs(value).format("DD.MM")}
            tick={{ fill: token.colorTextSecondary }}
            stroke={token.colorBorder}
            minTickGap={16}
          />
          <YAxis
            width={64}
            tick={{ fill: token.colorTextSecondary }}
            stroke={token.colorBorder}
            domain={["auto", "auto"]}
          />
          <Tooltip
            labelFormatter={(value) => dayjs(String(value)).format("DD.MM.YYYY")}
            formatter={(_value, _name, item) => [
              `${String(item.payload.rate)} RUB за 1 ${currencyCode}`,
              "Курс",
            ]}
            contentStyle={{
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadius,
              color: token.colorText,
            }}
            itemStyle={{ color: token.colorText }}
            labelStyle={{ color: token.colorText }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={token.blue}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

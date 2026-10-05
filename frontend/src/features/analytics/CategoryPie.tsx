import { Flex, theme, Typography } from "antd";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { formatAmount } from "@/shared/ui";
import { type CategoryRow, foldRows, OTHER_ROW_ID, shareOf } from "./categoryRows";

/** Не больше семи именованных секторов: остальное — «Прочие» (больше цветов на круге не различить). */
const MAX_SLICES = 7;

export interface CategoryPieProps {
  rows: CategoryRow[];
  total: string;
  currencyCode: string;
}

export function CategoryPie({ rows, total, currencyCode }: CategoryPieProps) {
  const { token } = theme.useToken();
  const palette = [
    token.blue,
    token.orange,
    token.green,
    token.purple,
    token.cyan,
    token.magenta,
    token.gold,
  ];
  const slices = foldRows(rows, MAX_SLICES).map((row, index) => ({
    ...row,
    value: Number(row.amount),
    color: row.id === OTHER_ROW_ID ? token.colorTextQuaternary : palette[index % palette.length],
  }));

  return (
    <Flex vertical gap={16}>
      <div role="img" aria-label="Круговая диаграмма расходов по категориям">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              innerRadius="55%"
              outerRadius="90%"
              paddingAngle={2}
              stroke={token.colorBgContainer}
              strokeWidth={2}
            >
              {slices.map((slice) => (
                <Cell key={slice.id} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [`${formatAmount(String(value))} ${currencyCode}`, name]}
              contentStyle={{
                background: token.colorBgElevated,
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: token.borderRadius,
                color: token.colorText,
              }}
              itemStyle={{ color: token.colorText }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <Flex vertical gap={8} role="list" aria-label="Легенда диаграммы">
        {slices.map((slice) => (
          <Flex key={slice.id} role="listitem" align="center" justify="space-between" gap={8}>
            <Flex align="center" gap={8} style={{ minWidth: 0 }}>
              <span
                aria-hidden
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 2,
                  flex: "none",
                  background: slice.color,
                }}
              />
              <Typography.Text ellipsis>{slice.name}</Typography.Text>
            </Flex>
            <Typography.Text>
              {formatAmount(slice.amount)} {currencyCode} · {shareOf(slice, total).toFixed(1)}%
            </Typography.Text>
          </Flex>
        ))}
      </Flex>
    </Flex>
  );
}

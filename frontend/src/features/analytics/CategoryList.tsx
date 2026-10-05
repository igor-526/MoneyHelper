import { Flex, theme, Typography } from "antd";
import { formatAmount, Icon } from "@/shared/ui";
import { type CategoryRow, shareOf } from "./categoryRows";

export interface CategoryListProps {
  rows: CategoryRow[];
  total: string;
  currencyCode: string;
}

/** Первая строка — «По всем категориям» (итог), далее категории в порядке `rows`. */
export function CategoryList({ rows, total, currencyCode }: CategoryListProps) {
  const { token } = theme.useToken();
  const rowStyle = {
    padding: `${token.paddingSM}px 0`,
    borderBottom: `1px solid ${token.colorBorderSecondary}`,
  };

  return (
    <Flex vertical role="list" aria-label="Расходы по категориям">
      <Flex role="listitem" justify="space-between" gap={8} style={rowStyle}>
        <Typography.Text strong>По всем категориям</Typography.Text>
        <Typography.Text strong>
          {formatAmount(total)} {currencyCode}
        </Typography.Text>
      </Flex>
      {rows.map((row) => (
        <Flex key={row.id} role="listitem" justify="space-between" gap={8} style={rowStyle}>
          <Flex align="center" gap={8} style={{ minWidth: 0 }}>
            {row.icon ? <Icon name={row.icon} /> : null}
            <Typography.Text ellipsis>{row.name}</Typography.Text>
          </Flex>
          <Flex vertical align="flex-end">
            <Typography.Text>
              {formatAmount(row.amount)} {currencyCode}
            </Typography.Text>
            <Typography.Text type="secondary">{shareOf(row, total).toFixed(1)}%</Typography.Text>
          </Flex>
        </Flex>
      ))}
    </Flex>
  );
}

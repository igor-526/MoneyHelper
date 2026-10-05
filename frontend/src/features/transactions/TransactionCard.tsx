import { Card, Flex, Typography } from "antd";
import dayjs from "dayjs";
import type { KeyboardEvent } from "react";
import { formatAmount, Icon } from "@/shared/ui";
import type { Transaction } from "./Transaction";

export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string } | undefined;
  currencyCodeById: Map<string, string>;
  onEdit: (transaction: Transaction) => void;
}

/** Компактная карточка пополнения или расхода; нажатие на неё открывает форму редактирования. */
export function TransactionCard({
  transaction,
  walletName,
  category,
  currencyCodeById,
  onEdit,
}: TransactionCardProps) {
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onEdit(transaction);
    }
  };

  return (
    <Card
      size="small"
      hoverable
      role="button"
      tabIndex={0}
      onClick={() => onEdit(transaction)}
      onKeyDown={handleKeyDown}
    >
      <Flex vertical gap={4}>
        <Flex align="center" justify="space-between" gap={8}>
          <Flex align="center" gap={8} style={{ minWidth: 0 }}>
            {category ? <Icon name={category.icon} /> : null}
            <Typography.Text strong ellipsis>
              {category?.name ?? "…"}
            </Typography.Text>
          </Flex>
          <Flex vertical align="flex-end">
            {transaction.legs.map((leg) => (
              <Typography.Text key={leg.currency_id} strong>
                {formatAmount(leg.amount)} {currencyCodeById.get(leg.currency_id) ?? "…"}
              </Typography.Text>
            ))}
          </Flex>
        </Flex>
        <Typography.Text type="secondary" ellipsis>
          {walletName ?? "…"} · {dayjs(transaction.occurred_at).format("DD.MM.YYYY HH:mm")}
        </Typography.Text>
        {transaction.comment ? (
          <Typography.Text type="secondary" ellipsis>
            {transaction.comment}
          </Typography.Text>
        ) : null}
      </Flex>
    </Card>
  );
}

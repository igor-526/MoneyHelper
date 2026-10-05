import { Button, Card, Flex, Popconfirm, Typography } from "antd";
import dayjs from "dayjs";
import { formatAmount, Icon } from "@/shared/ui";
import type { TransactionKind } from "./operationKinds";
import type { Transaction } from "./Transaction";

export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string } | undefined;
  currencyCodeById: Map<string, string>;
  kind: Pick<TransactionKind, "useDelete" | "deleteTitle">;
  onEdit: (transaction: Transaction) => void;
}

/** Карточка пополнения или расхода; сама владеет удалением (через `kind.useDelete`), как `WalletCard`. */
export function TransactionCard({
  transaction,
  walletName,
  category,
  currencyCodeById,
  kind,
  onEdit,
}: TransactionCardProps) {
  const deleteOperation = kind.useDelete();

  return (
    <Card>
      <Flex vertical gap={12}>
        <Typography.Text type="secondary">{walletName ?? "…"}</Typography.Text>
        <Flex align="center" gap={8}>
          {category ? <Icon name={category.icon} /> : null}
          <Typography.Text strong>{category?.name ?? "…"}</Typography.Text>
        </Flex>
        <Flex vertical gap={4}>
          {transaction.legs.map((leg) => (
            <Typography.Text key={leg.currency_id}>
              {formatAmount(leg.amount)} {currencyCodeById.get(leg.currency_id) ?? "…"}
            </Typography.Text>
          ))}
        </Flex>
        {transaction.comment ? (
          <Typography.Text type="secondary">{transaction.comment}</Typography.Text>
        ) : null}
        <Typography.Text type="secondary">
          {dayjs(transaction.occurred_at).format("DD.MM.YYYY HH:mm")}
        </Typography.Text>
        <Flex gap={8}>
          <Button onClick={() => onEdit(transaction)}>Редактировать</Button>
          <Popconfirm
            title={kind.deleteTitle}
            okText="Удалить"
            okType="danger"
            cancelText="Отмена"
            onConfirm={() => deleteOperation.mutate(transaction.id)}
          >
            <Button danger loading={deleteOperation.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Flex>
      </Flex>
    </Card>
  );
}

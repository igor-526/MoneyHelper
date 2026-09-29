import { Button, Card, Flex, Tag, Typography, Popconfirm } from "antd";
import dayjs from "dayjs";
import type { CategoryType } from "@/features/categories/Category";
import { Icon } from "@/shared/ui";
import type { Transaction } from "./Transaction";
import { useDeleteTransaction } from "./useDeleteTransaction";

export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string; type: CategoryType } | undefined;
  currencyCode: string | undefined;
  onEdit: (transaction: Transaction) => void;
}

/**
 * Локальная копия таблицы из `CategoryCard` (015), не импорт из `features/categories` — в проекте нет
 * прецедента импорта одной фичи из другой для UI-таблиц, а сама таблица — три строки без логики (design.md).
 */
const TYPE_TAG: Record<CategoryType, { label: string; color: "success" | "error" }> = {
  income: { label: "Доход", color: "success" },
  expense: { label: "Расход", color: "error" },
};

/** Сама владеет удалением (по образцу `WalletCard`/`CategoryCard`) — не получает мутацию от родителя. */
export function TransactionCard({
  transaction,
  walletName,
  category,
  currencyCode,
  onEdit,
}: TransactionCardProps) {
  const deleteTransaction = useDeleteTransaction();
  const typeTag = category ? TYPE_TAG[category.type] : undefined;
  const leg = transaction.legs[0];

  return (
    <Card>
      <Flex vertical gap={12}>
        <Typography.Text type="secondary">{walletName ?? "…"}</Typography.Text>
        <Flex align="center" gap={8}>
          {category ? <Icon name={category.icon} /> : null}
          <Typography.Text strong>{category?.name ?? "…"}</Typography.Text>
          {typeTag ? <Tag color={typeTag.color}>{typeTag.label}</Tag> : null}
        </Flex>
        <Typography.Text>
          {leg?.amount ?? "…"} {currencyCode ?? "…"}
        </Typography.Text>
        <Typography.Text type="secondary">
          {dayjs(transaction.occurred_at).format("DD.MM.YYYY HH:mm")}
        </Typography.Text>
        <Flex gap={8}>
          <Button onClick={() => onEdit(transaction)}>Редактировать</Button>
          <Popconfirm
            title="Удалить операцию?"
            okText="Удалить"
            okType="danger"
            cancelText="Отмена"
            onConfirm={() => deleteTransaction.mutate(transaction.id)}
          >
            <Button danger loading={deleteTransaction.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Flex>
      </Flex>
    </Card>
  );
}

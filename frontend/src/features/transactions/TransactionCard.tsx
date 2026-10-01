import { Button, Card, Flex, Tag, Tooltip, Typography, Popconfirm } from "antd";
import dayjs from "dayjs";
import type { CategoryType } from "@/features/categories/Category";
import { Icon } from "@/shared/ui";
import type { Transaction } from "./Transaction";
import { useDeleteTransaction } from "./useDeleteTransaction";

const MULTI_LEG_TOOLTIP =
  "Пополнение с несколькими валютами нельзя редактировать — удалите и создайте заново";

export interface TransactionCardProps {
  transaction: Transaction;
  walletName: string | undefined;
  category: { name: string; icon: string; type: CategoryType } | undefined;
  currencyCodeById: Map<string, string>;
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
  currencyCodeById,
  onEdit,
}: TransactionCardProps) {
  const deleteTransaction = useDeleteTransaction();
  const typeTag = category ? TYPE_TAG[category.type] : undefined;
  const isMultiLeg = transaction.legs.length > 1;

  const editButton = (
    <Button disabled={isMultiLeg} onClick={() => onEdit(transaction)}>
      Редактировать
    </Button>
  );

  return (
    <Card>
      <Flex vertical gap={12}>
        <Typography.Text type="secondary">{walletName ?? "…"}</Typography.Text>
        <Flex align="center" gap={8}>
          {category ? <Icon name={category.icon} /> : null}
          <Typography.Text strong>{category?.name ?? "…"}</Typography.Text>
          {typeTag ? <Tag color={typeTag.color}>{typeTag.label}</Tag> : null}
        </Flex>
        {/*
          Одна строка «сумма код» при одной ноге, список таких строк (одна на каждую валюту) при нескольких —
          `Flex` с одним ребёнком визуально не отличим от одинокого `Typography.Text` (design.md, п. 4.2), а
          единый рендер через `.map()` избегает индексации `legs[0]`, небезопасной при `noUncheckedIndexedAccess`.
        */}
        <Flex vertical gap={4}>
          {transaction.legs.map((leg) => (
            <Typography.Text key={leg.currency_id}>
              {leg.amount} {currencyCodeById.get(leg.currency_id) ?? "…"}
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
          {/* antd Tooltip не всплывает над disabled-элементом без обёртки — стандартный приём antd. */}
          {isMultiLeg ? (
            <Tooltip title={MULTI_LEG_TOOLTIP}>
              <span>{editButton}</span>
            </Tooltip>
          ) : (
            editButton
          )}
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

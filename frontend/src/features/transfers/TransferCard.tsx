import { Button, Card, Flex, Popconfirm, Typography } from "antd";
import dayjs from "dayjs";
import { formatAmount } from "@/shared/ui";
import type { Transfer } from "./Transfer";
import { useDeleteTransfer } from "./useDeleteTransfer";

export interface TransferCardProps {
  transfer: Transfer;
  fromWalletName: string | undefined;
  toWalletName: string | undefined;
  currencyCode: string | undefined;
  onEdit: (transfer: Transfer) => void;
}

/**
 * Сама владеет удалением (по образцу `TransactionCard`/`WalletCard`) — не получает мутацию от родителя. Без
 * блокировки редактирования — у перевода всегда ровно одна валюта, задел 016/017 про многоногие операции
 * переводов не касается (design.md).
 */
export function TransferCard({
  transfer,
  fromWalletName,
  toWalletName,
  currencyCode,
  onEdit,
}: TransferCardProps) {
  const deleteTransfer = useDeleteTransfer();

  return (
    <Card>
      <Flex vertical gap={12}>
        <Typography.Text strong>
          {fromWalletName ?? "…"} → {toWalletName ?? "…"}
        </Typography.Text>
        <Typography.Text>
          {formatAmount(transfer.amount)} {currencyCode ?? "…"}
        </Typography.Text>
        <Typography.Text type="secondary">
          {dayjs(transfer.occurred_at).format("DD.MM.YYYY HH:mm")}
        </Typography.Text>
        <Flex gap={8}>
          <Button onClick={() => onEdit(transfer)}>Редактировать</Button>
          <Popconfirm
            title="Удалить перевод?"
            okText="Удалить"
            okType="danger"
            cancelText="Отмена"
            onConfirm={() => deleteTransfer.mutate(transfer.id)}
          >
            <Button danger loading={deleteTransfer.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Flex>
      </Flex>
    </Card>
  );
}

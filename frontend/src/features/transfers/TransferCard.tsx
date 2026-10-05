import { Card, Flex, Typography } from "antd";
import dayjs from "dayjs";
import type { KeyboardEvent } from "react";
import { formatAmount } from "@/shared/ui";
import type { Transfer } from "./Transfer";

export interface TransferCardProps {
  transfer: Transfer;
  fromWalletName: string | undefined;
  toWalletName: string | undefined;
  currencyCode: string | undefined;
  onEdit: (transfer: Transfer) => void;
}

/** Компактная карточка перевода; нажатие на неё открывает форму редактирования. */
export function TransferCard({
  transfer,
  fromWalletName,
  toWalletName,
  currencyCode,
  onEdit,
}: TransferCardProps) {
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onEdit(transfer);
    }
  };

  return (
    <Card
      size="small"
      hoverable
      role="button"
      tabIndex={0}
      onClick={() => onEdit(transfer)}
      onKeyDown={handleKeyDown}
    >
      <Flex vertical gap={4}>
        <Flex align="center" justify="space-between" gap={8}>
          <Typography.Text strong ellipsis>
            {fromWalletName ?? "…"} → {toWalletName ?? "…"}
          </Typography.Text>
          <Typography.Text strong>
            {formatAmount(transfer.amount)} {currencyCode ?? "…"}
          </Typography.Text>
        </Flex>
        <Typography.Text type="secondary">
          {dayjs(transfer.occurred_at).format("DD.MM.YYYY HH:mm")}
        </Typography.Text>
      </Flex>
    </Card>
  );
}

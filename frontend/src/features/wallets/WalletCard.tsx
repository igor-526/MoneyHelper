import { Button, Card, Flex, Popconfirm, Tag, Typography } from "antd";
import { Icon } from "@/shared/ui";
import type { Wallet } from "./Wallet";
import { useDeleteWallet } from "./useDeleteWallet";

export interface WalletCardProps {
  wallet: Wallet;
  /** Коды валют кошелька, в порядке `wallet.currency_ids` (backend уже отсортировал по коду). */
  currencyCodes: string[];
  onEdit: (wallet: Wallet) => void;
}

/** Сама владеет удалением (по образцу `LogoutButton`) — не получает мутацию от родителя. */
export function WalletCard({ wallet, currencyCodes, onEdit }: WalletCardProps) {
  const deleteWallet = useDeleteWallet();

  return (
    <Card>
      <Flex vertical gap={12}>
        <Flex align="center" gap={8}>
          <Icon name={wallet.icon} />
          <Typography.Text strong>{wallet.name}</Typography.Text>
        </Flex>
        <Flex wrap gap={4}>
          {currencyCodes.map((code) => (
            <Tag key={code}>{code}</Tag>
          ))}
        </Flex>
        <Flex gap={8}>
          <Button onClick={() => onEdit(wallet)}>Редактировать</Button>
          <Popconfirm
            title={`Удалить кошелёк «${wallet.name}»?`}
            okText="Удалить"
            okType="danger"
            cancelText="Отмена"
            onConfirm={() => deleteWallet.mutate(wallet.id)}
          >
            <Button danger loading={deleteWallet.isPending}>
              Удалить
            </Button>
          </Popconfirm>
        </Flex>
      </Flex>
    </Card>
  );
}

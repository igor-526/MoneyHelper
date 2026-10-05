import { Button, Card, Flex, Popconfirm, Tag, Typography } from "antd";
import { Icon } from "@/shared/ui";
import type { Wallet } from "./Wallet";
import { useDeleteWallet } from "./useDeleteWallet";

export interface WalletCardProps {
  wallet: Wallet;
  /** Код валюты кошелька; `undefined`, пока справочник валют не загружен. */
  currencyCode: string | undefined;
  onEdit: (wallet: Wallet) => void;
}

/** Сама владеет удалением (по образцу `LogoutButton`) — не получает мутацию от родителя. */
export function WalletCard({ wallet, currencyCode, onEdit }: WalletCardProps) {
  const deleteWallet = useDeleteWallet();

  return (
    <Card>
      <Flex vertical gap={12}>
        <Flex align="center" gap={8}>
          <Icon name={wallet.icon} />
          <Typography.Text strong>{wallet.name}</Typography.Text>
        </Flex>
        {currencyCode !== undefined ? (
          <Tag style={{ alignSelf: "flex-start" }}>{currencyCode}</Tag>
        ) : null}
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

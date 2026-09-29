import { Card, Flex, Spin, Typography } from "antd";
import { useWalletBalances } from "./useWalletBalances";

export interface WalletBalanceCardProps {
  walletId: string;
  /** Map id -> код валюты, из уже загруженного `useCurrencies()` (та же техника, что и в `TransactionCard`). */
  currencyCodeById: Map<string, string>;
}

/** Баланс выбранного кошелька по валютам (design.md, раздел «WalletBalanceCard»). Владеет своим запросом. */
export function WalletBalanceCard({ walletId, currencyCodeById }: WalletBalanceCardProps) {
  const balancesQuery = useWalletBalances(walletId);

  if (balancesQuery.isPending) {
    return (
      <Card>
        <Spin />
      </Card>
    );
  }

  if (balancesQuery.isError) {
    return null;
  }

  return (
    <Card title="Баланс кошелька">
      <Flex vertical gap={4}>
        {balancesQuery.data.map((balance) => (
          <Typography.Text key={balance.currency_id}>
            {currencyCodeById.get(balance.currency_id) ?? "…"}: {balance.balance}
          </Typography.Text>
        ))}
      </Flex>
    </Card>
  );
}

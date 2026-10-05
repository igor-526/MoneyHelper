import { Card, Spin, Typography } from "antd";
import { formatAmount } from "@/shared/ui";
import { useWalletBalances } from "./useWalletBalances";

export interface WalletBalanceCardProps {
  walletId: string;
  /** Map id -> код валюты, из уже загруженного `useCurrencies()` (та же техника, что и в `TransactionCard`). */
  currencyCodeById: Map<string, string>;
}

/** Баланс выбранного кошелька одной суммой (design.md, раздел «WalletBalanceCard»). Владеет своим запросом. */
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
      <Typography.Text>
        {currencyCodeById.get(balancesQuery.data.currency_id) ?? "…"}:{" "}
        {formatAmount(balancesQuery.data.balance)}
      </Typography.Text>
    </Card>
  );
}

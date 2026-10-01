import { Card, Flex, Spin, Typography } from "antd";
import type { Wallet } from "./Wallet";
import { useWalletRates } from "./useWalletRates";

export interface WalletRateCardProps {
  wallet: Wallet;
  /** Map id -> код валюты, из уже загруженного `useCurrencies()` (та же техника, что и в `WalletBalanceCard`). */
  currencyCodeById: Map<string, string>;
}

/**
 * Средний курс многовалютного кошелька (021) относительно первой по коду валюты кошелька (`currency_ids[0]` —
 * backend уже отдаёт валюты отсортированными по коду). Не рендерится для кошелька с одной валютой — курсу не с
 * чем сравниваться (design.md, раздел 7).
 */
export function WalletRateCard({ wallet, currencyCodeById }: WalletRateCardProps) {
  const targetCurrencyId = wallet.currency_ids[0];
  const hasMultipleCurrencies = wallet.currency_ids.length > 1 && targetCurrencyId !== undefined;
  const ratesQuery = useWalletRates(wallet.id, targetCurrencyId ?? "", hasMultipleCurrencies);

  if (!hasMultipleCurrencies) {
    return null;
  }

  if (ratesQuery.isPending) {
    return (
      <Card>
        <Spin />
      </Card>
    );
  }

  if (ratesQuery.isError) {
    return null;
  }

  const targetCode = currencyCodeById.get(targetCurrencyId) ?? "…";

  return (
    <Card title="Курс кошелька">
      <Flex vertical gap={4}>
        {ratesQuery.data.rates.map((rate) => (
          <Typography.Text key={rate.currency_id}>
            1 {currencyCodeById.get(rate.currency_id) ?? "…"} ≈ {rate.rate} {targetCode}
          </Typography.Text>
        ))}
        {ratesQuery.data.unrated_currency_ids.map((currencyId) => (
          <Typography.Text key={currencyId} type="secondary">
            {currencyCodeById.get(currencyId) ?? "…"}: нет данных для курса
          </Typography.Text>
        ))}
      </Flex>
    </Card>
  );
}

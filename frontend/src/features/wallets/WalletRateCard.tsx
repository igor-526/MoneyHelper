import { Card, Flex, Spin, Typography } from "antd";
import { formatAmount } from "@/shared/ui";
import type { Wallet } from "./Wallet";
import { useWalletRates } from "./useWalletRates";

export interface WalletRateCardProps {
  wallet: Wallet;
  /** Map id -> код валюты, из уже загруженного `useCurrencies()` (та же техника, что и в `WalletBalanceCard`). */
  currencyCodeById: Map<string, string>;
}

/**
 * Средний курс кошелька к валюте воркспейса (029). Не рендерится, если валюты совпадают или запрос завершился
 * ошибкой (уведомление показывает глобальный обработчик); при отсутствии пополнений с обеими ногами объясняет это.
 */
export function WalletRateCard({ wallet, currencyCodeById }: WalletRateCardProps) {
  const ratesQuery = useWalletRates(wallet.id);

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

  const { workspace_currency_id, wallet_currency_id, rate } = ratesQuery.data;
  if (workspace_currency_id === wallet_currency_id) {
    return null;
  }

  return (
    <Card title="Курс кошелька">
      {rate === null ? (
        <Typography.Text type="secondary">
          Курс пока не определён: пополните кошелёк, указав суммы в обеих валютах.
        </Typography.Text>
      ) : (
        <Flex vertical gap={4}>
          <Typography.Text>
            1 {currencyCodeById.get(wallet_currency_id) ?? "…"} ≈ {formatAmount(rate, 0)}{" "}
            {currencyCodeById.get(workspace_currency_id) ?? "…"}
          </Typography.Text>
          <Typography.Text type="secondary">
            Среднее по пополнениям этого кошелька за всё время
          </Typography.Text>
        </Flex>
      )}
    </Card>
  );
}

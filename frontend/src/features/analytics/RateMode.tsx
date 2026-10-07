import { Flex, Select, Spin, Table, Typography } from "antd";
import { useMemo, useState } from "react";
import { useWallets } from "@/features/wallets/useWallets";
import { useCurrentWorkspace } from "@/features/workspaces/useCurrentWorkspace";
import { EmptyState, useCurrencies } from "@/shared/ui";
import type { AnalyticsRange } from "./Analytics";
import { ExchangeRateChart } from "./ExchangeRateChart";
import { rateCurrencies } from "./rateCurrencies";
import { rateStats } from "./rateStats";
import { useExchangeRateHistory } from "./useExchangeRateHistory";

export function RateMode({ range }: { range: AnalyticsRange }) {
  const workspace = useCurrentWorkspace();
  const { data: wallets = [], isPending: walletsPending } = useWallets();
  const { data: currencies = [], isPending: currenciesPending } = useCurrencies();
  const options = useMemo(
    () => rateCurrencies(workspace?.currency_id, wallets, currencies),
    [workspace?.currency_id, wallets, currencies],
  );
  const [selectedCurrencyId, setSelectedCurrencyId] = useState<string>();
  const currencyId = options.some((currency) => currency.id === selectedCurrencyId)
    ? selectedCurrencyId
    : options[0]?.id;

  const selectedCurrency = options.find((currency) => currency.id === currencyId);
  const query = useExchangeRateHistory(currencyId, range);
  const points = useMemo(() => query.data?.points ?? [], [query.data?.points]);
  const stats = useMemo(() => rateStats(points), [points]);
  const isLoadingOptions = walletsPending || currenciesPending;

  if (isLoadingOptions) return <Spin />;
  if (options.length === 0) {
    return <EmptyState icon="trending-up" title="Нет валют для расчёта курса к RUB" />;
  }

  return (
    <Flex vertical gap={16}>
      <Flex vertical gap={4}>
        <Typography.Text strong>Валюта</Typography.Text>
        <Select
          aria-label="Валюта курса"
          value={currencyId}
          onChange={setSelectedCurrencyId}
          options={options.map((currency) => ({
            value: currency.id,
            label: `${currency.code} — ${currency.name}`,
          }))}
        />
      </Flex>
      {query.isPending ? (
        <Spin />
      ) : points.length > 0 && selectedCurrency ? (
        <Flex vertical gap={16}>
          <ExchangeRateChart points={points} currencyCode={selectedCurrency.code} />
          <Table
            aria-label="Статистика курса"
            rowKey="label"
            pagination={false}
            size="small"
            dataSource={stats.map((item) => ({
              ...item,
              value: `${item.value} RUB за 1 ${selectedCurrency.code}`,
            }))}
            columns={[
              { title: "Показатель", dataIndex: "label" },
              { title: "Значение", dataIndex: "value", align: "right" },
            ]}
          />
        </Flex>
      ) : (
        <EmptyState icon="trending-up" title="Нет данных о курсе за выбранный период" />
      )}
    </Flex>
  );
}

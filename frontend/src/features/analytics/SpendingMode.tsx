import { Alert, Badge, Button, Flex, Spin, Table, Typography } from "antd";
import { useMemo, useState } from "react";
import { useCurrentWorkspace } from "@/features/workspaces/useCurrentWorkspace";
import { EmptyState, formatAmount, Icon, useCurrencies } from "@/shared/ui";
import type { AnalyticsRange } from "./Analytics";
import { buildDailySpending, totalSpending } from "./dailySpending";
import { SpendingChart } from "./SpendingChart";
import { countSpendingFilters, EMPTY_SPENDING_FILTERS } from "./spendingFilters";
import { SpendingFiltersPopup } from "./SpendingFiltersPopup";
import { unconvertedMessage } from "./unconvertedMessage";
import { useAnalytics } from "./useAnalytics";
import { spendingStats } from "./spendingStats";

/** Режим «Трата»: график расходов по дням в валюте воркспейса; фильтры по кошельку и категории — в окне. */
export function SpendingMode({ range }: { range: AnalyticsRange }) {
  const [filters, setFilters] = useState(EMPTY_SPENDING_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const query = useAnalytics({
    ...range,
    groupBy: "day",
    type: "expense",
    walletId: filters.walletId,
    categoryId: filters.categoryId,
  });
  const { data: currencies = [] } = useCurrencies();
  const workspace = useCurrentWorkspace();

  const currencyCode =
    currencies.find((currency) => currency.id === workspace?.currency_id)?.code ?? "…";
  const series = useMemo(
    () => buildDailySpending(query.data?.buckets ?? [], range),
    [query.data, range],
  );
  const unconvertedCodes = (query.data?.unconverted_currencies ?? []).map(
    (id) => currencies.find((currency) => currency.id === id)?.code ?? "…",
  );
  const hasSpending = (query.data?.buckets ?? []).length > 0;
  const stats = useMemo(() => spendingStats(series), [series]);

  return (
    <Flex vertical gap={16}>
      <Flex align="center" justify="space-between" gap={8}>
        <Typography.Text strong>
          {query.isSuccess && hasSpending
            ? `Всего: ${formatAmount(totalSpending(series))} ${currencyCode}`
            : "Траты по дням"}
        </Typography.Text>
        <Badge count={countSpendingFilters(filters)} size="small">
          <Button
            aria-label="Фильтры"
            icon={<Icon name="funnel" />}
            onClick={() => setFiltersOpen(true)}
          />
        </Badge>
      </Flex>
      {unconvertedCodes.length > 0 ? (
        <Alert type="warning" title={unconvertedMessage(unconvertedCodes, currencyCode)} />
      ) : null}
      {query.isPending ? (
        <Spin />
      ) : hasSpending ? (
        <Flex vertical gap={16}>
          <SpendingChart series={series} currencyCode={currencyCode} />
          <Table
            aria-label="Статистика дневных трат"
            rowKey="label"
            pagination={false}
            size="small"
            dataSource={stats.map((item) => ({
              ...item,
              value: `${formatAmount(item.value)} ${currencyCode}`,
            }))}
            columns={[
              { title: "Показатель", dataIndex: "label" },
              { title: "Значение", dataIndex: "value", align: "right" },
            ]}
          />
        </Flex>
      ) : (
        <EmptyState icon="trending-up" title="Нет расходов за выбранный период" />
      )}
      <SpendingFiltersPopup
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        value={filters}
        onApply={setFilters}
      />
    </Flex>
  );
}

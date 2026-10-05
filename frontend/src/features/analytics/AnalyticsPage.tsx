import { Alert, DatePicker, Flex, Segmented, Select, Spin, Typography } from "antd";
import type { Dayjs } from "dayjs";
import { useMemo, useState } from "react";
import type { CategoryType } from "@/features/categories/Category";
import { useCategories } from "@/features/categories/useCategories";
import { useCurrentWorkspace } from "@/features/workspaces/useCurrentWorkspace";
import { useWallets } from "@/features/wallets/useWallets";
import { CurrencyPicker, EmptyState, useCurrencies } from "@/shared/ui";
import { AnalyticsBucketCard } from "./AnalyticsBucketCard";
import type { GroupBy } from "./Analytics";
import {
  allowedDisplayCurrencyIds,
  unconvertedMessage,
  walletCurrencyIds,
} from "./analyticsCurrencies";
import { INITIAL_ANALYTICS_STATE, buildAnalyticsFilters } from "./buildAnalyticsFilters";
import { useAnalytics } from "./useAnalytics";
import { useBucketLabelResolvers } from "./useBucketLabelResolvers";

const ALL_WALLETS = "all";
const ALL_CATEGORIES = "all";
const ALL_TYPES = "all";
const ALL_CURRENCIES = "all";
type TypeFilter = "all" | CategoryType;

const GROUP_BY_OPTIONS: { label: string; value: GroupBy }[] = [
  { label: "Кошелёк", value: "wallet" },
  { label: "Категория", value: "category" },
  { label: "Валюта", value: "currency" },
];

const TYPE_FILTER_OPTIONS: { label: string; value: TypeFilter }[] = [
  { label: "Все типы", value: ALL_TYPES },
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

export function AnalyticsPage() {
  const [state, setState] = useState(INITIAL_ANALYTICS_STATE);

  const { data: wallets = [] } = useWallets();
  const { data: allCategories = [] } = useCategories(undefined);
  const { data: currencies = [] } = useCurrencies();
  const workspace = useCurrentWorkspace();

  const displayCurrencyIds = useMemo(
    () => allowedDisplayCurrencyIds(workspace?.currency_id, wallets),
    [workspace, wallets],
  );
  const operationCurrencyIds = useMemo(() => walletCurrencyIds(wallets), [wallets]);

  const currencyCodeById = useMemo(
    () => new Map(currencies.map((c) => [c.id, c.code])),
    [currencies],
  );

  const filters = useMemo(() => buildAnalyticsFilters(state), [state]);
  const analyticsQuery = useAnalytics(filters);
  const labelResolvers = useBucketLabelResolvers();

  const updateState = (patch: Partial<typeof state>) => {
    setState((prev) => ({ ...prev, ...patch }));
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      updateState({ dateRange: [dates[0], dates[1]] });
    } else {
      updateState({ dateRange: null });
    }
  };

  const resolveLabel = filters ? labelResolvers[filters.groupBy] : undefined;
  const sortedBuckets = useMemo(() => {
    if (!analyticsQuery.data || !resolveLabel) return [];
    return analyticsQuery.data.buckets
      .map((bucket) => ({ bucket, label: resolveLabel(bucket.group_key) ?? "…" }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [analyticsQuery.data, resolveLabel]);

  const displayCurrencyCode = analyticsQuery.data
    ? (currencyCodeById.get(analyticsQuery.data.display_currency_id) ?? "…")
    : undefined;

  const unconvertedCodes = (analyticsQuery.data?.unconverted_currencies ?? []).map(
    (id) => currencyCodeById.get(id) ?? "…",
  );

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Аналитика
      </Typography.Title>
      <Flex vertical gap={12}>
        {/* `role="group"` — `CurrencyPicker` не пробрасывает `aria-label` во внутренний `Select` (в отличие от
            обычных `Select` ниже), поэтому доступное имя для тестов и вспомогательных технологий даёт обёртка. */}
        <div role="group" aria-label="Валюта отображения">
          <CurrencyPicker
            value={state.displayCurrencyId ?? workspace?.currency_id}
            onChange={(value) => updateState({ displayCurrencyId: value })}
            allowedIds={displayCurrencyIds}
            allowClear={false}
            placeholder="Валюта отображения"
          />
        </div>
        <DatePicker.RangePicker
          aria-label="Диапазон дат"
          placeholder={["Дата от", "Дата до"]}
          value={state.dateRange}
          onChange={handleDateRangeChange}
          allowClear
        />
        <Segmented
          aria-label="Срез"
          options={GROUP_BY_OPTIONS}
          // `value={state.groupBy ?? ""}`, а не `undefined` напрямую: при `value={undefined}` `Segmented`
          // визуально подсвечивает первую опцию как активную (внутреннее поведение antd), но не вызывает
          // `onChange` при клике по ней — пользователь не может явно выбрать первый срез. Значение `""` не
          // совпадает ни с одной опцией, поэтому ни одна не подсвечена, а клик по любой (включая первую)
          // корректно меняет состояние.
          value={state.groupBy ?? ""}
          onChange={(value) => updateState({ groupBy: value as GroupBy })}
        />
        <Select
          aria-label="Кошелёк"
          value={state.walletId ?? ALL_WALLETS}
          options={[
            { value: ALL_WALLETS, label: "Все кошельки" },
            ...wallets.map((wallet) => ({ value: wallet.id, label: wallet.name })),
          ]}
          onChange={(value) => updateState({ walletId: value === ALL_WALLETS ? undefined : value })}
        />
        <Select
          aria-label="Категория"
          value={state.categoryId ?? ALL_CATEGORIES}
          options={[
            { value: ALL_CATEGORIES, label: "Все категории" },
            ...allCategories.map((category) => ({ value: category.id, label: category.name })),
          ]}
          onChange={(value) =>
            updateState({ categoryId: value === ALL_CATEGORIES ? undefined : value })
          }
        />
        <Select
          aria-label="Тип"
          value={state.type}
          options={TYPE_FILTER_OPTIONS}
          onChange={(value) => updateState({ type: value as TypeFilter })}
        />
        <Select
          aria-label="Валюта операции"
          value={state.currencyId ?? ALL_CURRENCIES}
          options={[
            { value: ALL_CURRENCIES, label: "Все валюты" },
            ...currencies
              .filter((currency) => operationCurrencyIds.includes(currency.id))
              .map((currency) => ({ value: currency.id, label: currency.code })),
          ]}
          onChange={(value) =>
            updateState({ currencyId: value === ALL_CURRENCIES ? undefined : value })
          }
        />
      </Flex>
      {filters === null ? (
        <Alert type="info" title="Выберите диапазон дат и срез, чтобы увидеть аналитику" />
      ) : analyticsQuery.isPending ? (
        <Spin />
      ) : (
        <>
          {unconvertedCodes.length > 0 ? (
            <Alert
              type="warning"
              title={unconvertedMessage(unconvertedCodes, displayCurrencyCode ?? "…")}
            />
          ) : null}
          {sortedBuckets.length === 0 ? (
            <EmptyState icon="trending-up" title="Нет данных за выбранный период" />
          ) : (
            <>
              <Typography.Text type="secondary">Суммы в {displayCurrencyCode}</Typography.Text>
              <Flex vertical gap={12}>
                {sortedBuckets.map(({ bucket, label }) => (
                  <AnalyticsBucketCard
                    key={bucket.group_key}
                    label={label}
                    bucket={bucket}
                    currencyCode={displayCurrencyCode}
                  />
                ))}
              </Flex>
            </>
          )}
        </>
      )}
    </Flex>
  );
}

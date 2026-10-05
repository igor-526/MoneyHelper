import { Alert, Button, Flex, Segmented, Spin } from "antd";
import { useMemo, useState } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useCurrentWorkspace } from "@/features/workspaces/useCurrentWorkspace";
import { EmptyState, useCurrencies } from "@/shared/ui";
import type { AnalyticsRange } from "./Analytics";
import { buildCategoryRows, type SortDirection, sortRows, totalAmount } from "./categoryRows";
import { CategoryList } from "./CategoryList";
import { CategoryPie } from "./CategoryPie";
import { unconvertedMessage } from "./unconvertedMessage";
import { useAnalytics } from "./useAnalytics";

type View = "list" | "chart";

const VIEW_OPTIONS: { label: string; value: View }[] = [
  { label: "Список", value: "list" },
  { label: "Диаграмма", value: "chart" },
];

const SORT_LABELS: Record<SortDirection, string> = {
  desc: "Сначала большие",
  asc: "Сначала меньшие",
};

/** Режим «Категории»: только расходы, суммы в валюте воркспейса. */
export function CategoriesMode({ range }: { range: AnalyticsRange }) {
  const [view, setView] = useState<View>("list");
  const [direction, setDirection] = useState<SortDirection>("desc");

  const query = useAnalytics({ ...range, groupBy: "category", type: "expense" });
  const { data: categories = [] } = useCategories("expense");
  const { data: currencies = [] } = useCurrencies();
  const workspace = useCurrentWorkspace();

  const currencyCode =
    currencies.find((currency) => currency.id === workspace?.currency_id)?.code ?? "…";
  const rows = useMemo(
    () =>
      buildCategoryRows(
        query.data?.buckets ?? [],
        new Map(categories.map((category) => [category.id, category])),
      ),
    [query.data, categories],
  );
  const total = totalAmount(rows);
  const unconvertedCodes = (query.data?.unconverted_currencies ?? []).map(
    (id) => currencies.find((currency) => currency.id === id)?.code ?? "…",
  );

  if (query.isPending) return <Spin />;

  return (
    <Flex vertical gap={16}>
      {unconvertedCodes.length > 0 ? (
        <Alert type="warning" title={unconvertedMessage(unconvertedCodes, currencyCode)} />
      ) : null}
      {rows.length === 0 ? (
        <EmptyState icon="trending-up" title="Нет расходов за выбранный период" />
      ) : (
        <>
          <Segmented
            aria-label="Представление"
            options={VIEW_OPTIONS}
            value={view}
            onChange={setView}
            block
          />
          {view === "list" ? (
            <>
              <Button
                style={{ alignSelf: "flex-start" }}
                onClick={() => setDirection(direction === "desc" ? "asc" : "desc")}
              >
                {SORT_LABELS[direction]}
              </Button>
              <CategoryList
                rows={sortRows(rows, direction)}
                total={total}
                currencyCode={currencyCode}
              />
            </>
          ) : (
            <CategoryPie rows={rows} total={total} currencyCode={currencyCode} />
          )}
        </>
      )}
    </Flex>
  );
}

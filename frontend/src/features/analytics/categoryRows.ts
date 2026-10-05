import type { Category } from "@/features/categories/Category";
import type { AnalyticsBucket } from "./Analytics";
import { sumAmounts } from "./sumAmounts";

export interface CategoryRow {
  id: string;
  name: string;
  icon: string | undefined;
  amount: string;
}

export type SortDirection = "desc" | "asc";

/** Расходы по категориям; категория, которой нет в справочнике (например удалена), получает прочерк. */
export function buildCategoryRows(
  buckets: AnalyticsBucket[],
  categoryById: Map<string, Category>,
): CategoryRow[] {
  return buckets
    .filter((bucket) => Number(bucket.expense) > 0)
    .map((bucket) => {
      const category = categoryById.get(bucket.group_key);
      return {
        id: bucket.group_key,
        name: category?.name ?? "…",
        icon: category?.icon,
        amount: bucket.expense,
      };
    });
}

export function sortRows(rows: CategoryRow[], direction: SortDirection): CategoryRow[] {
  const sign = direction === "desc" ? -1 : 1;
  return [...rows].sort(
    (a, b) => sign * (Number(a.amount) - Number(b.amount)) || a.name.localeCompare(b.name),
  );
}

export function totalAmount(rows: CategoryRow[]): string {
  return sumAmounts(rows.map((row) => row.amount));
}

/** Доля строки в итоге, 0..100 — только для отображения и геометрии диаграммы. */
export function shareOf(row: CategoryRow, total: string): number {
  const totalNumber = Number(total);
  return totalNumber > 0 ? (Number(row.amount) / totalNumber) * 100 : 0;
}

export const OTHER_ROW_ID = "other";

/** Для диаграммы: крупнейшие `limit` категорий остаются, остальные сворачиваются в «Прочие». */
export function foldRows(rows: CategoryRow[], limit: number): CategoryRow[] {
  const sorted = sortRows(rows, "desc");
  if (sorted.length <= limit) return sorted;
  const rest = sorted.slice(limit);
  return [
    ...sorted.slice(0, limit),
    {
      id: OTHER_ROW_ID,
      name: "Прочие",
      icon: undefined,
      amount: sumAmounts(rest.map((r) => r.amount)),
    },
  ];
}

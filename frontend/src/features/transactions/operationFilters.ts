import type { Dayjs } from "dayjs";

/** Фильтры вкладки операций; `categoryIds` есть только у вкладок с категориями (расход, пополнение). */
export interface OperationFiltersState {
  walletIds?: string[];
  categoryIds?: string[];
  commentQuery?: string;
  dateRange: [Dayjs, Dayjs] | null; // null = без фильтра
}

export const EMPTY_OPERATION_FILTERS: OperationFiltersState = {
  dateRange: null,
};

/** Число заданных фильтров — для значка на кнопке «Фильтры». */
export function countActiveFilters(filters: OperationFiltersState): number {
  return [filters.walletIds, filters.categoryIds, filters.dateRange].filter(
    (value) => value !== undefined && value !== null,
  ).length;
}

import type { Dayjs } from "dayjs";

/** Фильтры вкладки операций; `categoryId` есть только у вкладок с категориями (расход, пополнение). */
export interface OperationFiltersState {
  walletId: string | undefined; // undefined = «Все кошельки»
  categoryId: string | undefined; // undefined = «Все категории»
  dateRange: [Dayjs, Dayjs] | null; // null = без фильтра
}

export const EMPTY_OPERATION_FILTERS: OperationFiltersState = {
  walletId: undefined,
  categoryId: undefined,
  dateRange: null,
};

/** Число заданных фильтров — для значка на кнопке «Фильтры». */
export function countActiveFilters(filters: OperationFiltersState): number {
  return [filters.walletId, filters.categoryId, filters.dateRange].filter(
    (value) => value !== undefined && value !== null,
  ).length;
}

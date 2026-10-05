/** Фильтры режима «Трата»: отбор по кошельку и категории расходов. */
export interface SpendingFilters {
  walletId: string | undefined; // undefined = «Все кошельки»
  categoryId: string | undefined; // undefined = «Все категории»
}

export const EMPTY_SPENDING_FILTERS: SpendingFilters = {
  walletId: undefined,
  categoryId: undefined,
};

/** Число заданных фильтров — для значка на кнопке «Фильтры». */
export function countSpendingFilters(filters: SpendingFilters): number {
  return [filters.walletId, filters.categoryId].filter((value) => value !== undefined).length;
}

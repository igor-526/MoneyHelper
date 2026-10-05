import type { Dayjs } from "dayjs";
import type { CategoryType } from "@/features/categories/Category";
import type { AnalyticsFilters, GroupBy } from "./Analytics";

type TypeFilter = "all" | CategoryType;

export interface AnalyticsPageState {
  displayCurrencyId: string | undefined;
  dateRange: [Dayjs, Dayjs] | null;
  groupBy: GroupBy | undefined;
  walletId: string | undefined;
  categoryId: string | undefined;
  currencyId: string | undefined;
  type: TypeFilter;
}

export const INITIAL_ANALYTICS_STATE: AnalyticsPageState = {
  displayCurrencyId: undefined,
  dateRange: null,
  groupBy: undefined,
  walletId: undefined,
  categoryId: undefined,
  currencyId: undefined,
  type: "all",
};

/** Единственное место, решающее «все обязательные поля заполнены» — используется и для гейтинга запроса, и для
 *  выбора между `Alert` «недостаточно данных» и списком корзин (одно вычисление, не два независимых условия). */
export function buildAnalyticsFilters(state: AnalyticsPageState): AnalyticsFilters | null {
  if (state.dateRange === null || state.groupBy === undefined) {
    return null;
  }
  return {
    displayCurrencyId: state.displayCurrencyId,
    dateFrom: state.dateRange[0].startOf("day").toISOString(),
    dateTo: state.dateRange[1].endOf("day").toISOString(),
    groupBy: state.groupBy,
    walletId: state.walletId,
    categoryId: state.categoryId,
    currencyId: state.currencyId,
    type: state.type === "all" ? undefined : state.type,
  };
}

import type { CategoryType } from "@/features/categories/Category";

export type GroupBy = "wallet" | "category" | "currency";

/** Форма элемента `buckets` ответа backend (`AnalyticsBucketOut`) — без camelCase-маппинга. */
export interface AnalyticsBucket {
  group_key: string;
  income: string;
  expense: string;
}

/** Форма ответа backend (`AnalyticsOut`) — без camelCase-маппинга, тот же принцип, что у `Wallet`/`Transaction`. */
export interface AnalyticsResult {
  display_currency_id: string;
  buckets: AnalyticsBucket[];
  unconverted_currencies: string[];
}

/** Вход `useAnalytics`: два обязательных поля запроса (диапазон и срез), валюта отображения и сужающие опциональные. camelCase — как `TransferFilters`. */
export interface AnalyticsFilters {
  /** `undefined` — валюта воркспейса: параметр не передаётся, умолчание определяет backend. */
  displayCurrencyId: string | undefined;
  dateFrom: string;
  dateTo: string;
  groupBy: GroupBy;
  walletId?: string;
  categoryId?: string;
  currencyId?: string;
  type?: CategoryType;
}

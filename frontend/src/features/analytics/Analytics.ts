export type GroupBy = "wallet" | "category" | "currency" | "day";

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

/** Диапазон дат в ISO; границы необязательны — без них backend считает весь период воркспейса. */
export interface AnalyticsRange {
  dateFrom?: string;
  dateTo?: string;
}

/** Вход `useAnalytics`: срез, тип операций, диапазон и отбор. Валюта отображения — всегда валюта воркспейса. */
export interface AnalyticsFilters extends AnalyticsRange {
  groupBy: GroupBy;
  type?: "income" | "expense";
  walletId?: string;
  categoryId?: string;
}

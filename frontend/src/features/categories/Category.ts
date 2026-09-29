export type CategoryType = "income" | "expense";

/** Форма ответа backend (`CategoryOut`) — без camelCase-маппинга, тот же принцип, что и `Wallet` (design.md 014). */
export interface Category {
  id: string;
  type: CategoryType;
  name: string;
  icon: string;
  created_at: string;
  updated_at: string | null;
}

/** Форма тела запроса `CategoryCreate`/`CategoryUpdate`; совпадает с именами полей формы. */
export interface CategoryFormValues {
  type: CategoryType;
  name: string;
  icon: string;
}

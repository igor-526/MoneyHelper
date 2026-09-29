/** Форма ответа backend (`WalletOut`) — без camelCase-маппинга (design.md, раздел «Wallet»). */
export interface Wallet {
  id: string;
  name: string;
  icon: string;
  currency_ids: string[];
  created_at: string;
  updated_at: string | null;
}

/** Форма тела запроса `WalletCreate`/`WalletUpdate`; совпадает с именами полей формы. */
export interface WalletFormValues {
  name: string;
  icon: string;
  currency_ids: string[];
}

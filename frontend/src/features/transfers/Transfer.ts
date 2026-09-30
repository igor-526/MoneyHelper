/**
 * Форма ответа backend (`TransferOut`) — без camelCase-маппинга, тот же принцип, что и `Transaction`/`Wallet`
 * (design.md). Плоская, не ногозависимая — у перевода всегда одна валюта.
 */
export interface Transfer {
  id: string;
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at: string;
  created_at: string;
  updated_at: string | null;
}

/** Тело запроса `TransferCreate`/`TransferUpdate`. */
export interface TransferFormValues {
  from_wallet_id: string;
  to_wallet_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: string;
}

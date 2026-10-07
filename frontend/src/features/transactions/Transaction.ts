/** Форма элемента `legs` ответа backend (`TransactionLegOut`). */
export interface TransactionLeg {
  currency_id: string;
  amount: string;
}

/**
 * Форма ответа backend (`TransactionOut`) — без camelCase-маппинга. Общая для расхода (`/transactions`, одна нога
 * в валюте кошелька) и пополнения (`/topups`, одна или две ноги: валюта воркспейса и валюта кошелька).
 */
export interface Transaction {
  id: string;
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[];
  occurred_at: string;
  comment: string | null;
  created_at: string;
  updated_at: string | null;
}

/** Тело запроса расхода `TransactionCreate`/`TransactionUpdate`: валюта — валюта кошелька, не передаётся. */
export interface TransactionFormValues {
  wallet_id: string;
  category_id: string;
  amount: string;
  occurred_at?: string;
  comment?: string;
}

/** Тело запроса `TopupCreate`/`TopupUpdate`: ноги — валюта воркспейса и валюта кошелька (одна, если совпадают). */
export interface TopupFormValues {
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[];
  occurred_at?: string;
  comment?: string;
}

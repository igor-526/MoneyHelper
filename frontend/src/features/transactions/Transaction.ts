/** Форма элемента `legs` ответа backend (`TransactionLegOut`). */
export interface TransactionLeg {
  currency_id: string;
  amount: string;
}

/**
 * Форма ответа backend (`TransactionOut`) — без camelCase-маппинга, тот же принцип, что и `Wallet`/`Category`
 * (design.md 014/015). Ногозависимая: `legs` — массив из одного элемента для операций, созданных этой формой
 * (эндпоинт `/topups` с несколькими ногами создаёт отдельная задача 017, вне рамок здесь); карточка/форма всегда
 * работают с `transaction.legs[0]`.
 */
export interface Transaction {
  id: string;
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[];
  occurred_at: string;
  created_at: string;
  updated_at: string | null;
}

/** Тело запроса `TransactionCreate`/`TransactionUpdate`. `type` не входит — backend его не принимает. */
export interface TransactionFormValues {
  wallet_id: string;
  category_id: string;
  currency_id: string;
  amount: string;
  occurred_at?: string;
}

/** Форма элемента ответа backend (`WalletBalanceOut`). */
export interface WalletBalance {
  currency_id: string;
  balance: string;
}

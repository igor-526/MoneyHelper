/** Форма элемента `legs` ответа backend (`TransactionLegOut`). */
export interface TransactionLeg {
  currency_id: string;
  amount: string;
}

/**
 * Форма ответа backend (`TransactionOut`) — без camelCase-маппинга, тот же принцип, что и `Wallet`/`Category`
 * (design.md 014/015). Ногозависимая: обычная операция (доход/расход) — `legs` из одного элемента; пополнение
 * многовалютного кошелька (`/topups`, 017) — по одной ноге на каждую валюту кошелька. `TransactionCard`
 * отображает все ноги; `TransactionForm` (создание/редактирование обычной операции) работает только с
 * `transaction.legs[0]` — операции с несколькими ногами ею не редактируются (017).
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

/** Тело запроса `TopupCreate` — пополнение многовалютного кошелька, ровно по одной ноге на каждую его валюту. */
export interface TopupFormValues {
  wallet_id: string;
  category_id: string;
  legs: TransactionLeg[];
  occurred_at?: string;
}

/** Форма элемента ответа backend (`WalletBalanceOut`). */
export interface WalletBalance {
  currency_id: string;
  balance: string;
}

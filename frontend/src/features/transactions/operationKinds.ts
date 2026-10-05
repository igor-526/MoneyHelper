import type { UseQueryResult } from "@tanstack/react-query";
import { type ComponentType, createElement } from "react";
import type { CategoryType } from "@/features/categories/Category";
import type { Page } from "@/shared/api";
import { TransfersTab } from "@/features/transfers/TransfersTab";
import { OperationsTab } from "./OperationsTab";
import { TopupForm } from "./TopupForm";
import { TransactionForm } from "./TransactionForm";
import type { Transaction } from "./Transaction";
import { useTopups } from "./useTopups";
import {
  type OperationFilters,
  type OperationPagination,
  useTransactions,
} from "./useTransactions";

export interface OperationFormProps {
  open: boolean;
  onClose: () => void;
  /** `undefined` — форма создания; заданная операция — форма редактирования. */
  transaction?: Transaction;
}

/** Настройки вкладки пополнений или расходов: общий `OperationsTab` для обеих. */
export interface TransactionKind {
  categoryType: CategoryType;
  createLabel: string;
  emptyTitle: string;
  useList: (
    filters: OperationFilters,
    pagination: OperationPagination,
  ) => UseQueryResult<Page<Transaction>>;
  Form: ComponentType<OperationFormProps>;
}

export const TOPUP_KIND: TransactionKind = {
  categoryType: "income",
  createLabel: "Создать пополнение",
  emptyTitle: "Пополнений пока нет",
  useList: useTopups,
  Form: TopupForm,
};

export const EXPENSE_KIND: TransactionKind = {
  categoryType: "expense",
  createLabel: "Создать расход",
  emptyTitle: "Расходов пока нет",
  useList: useTransactions,
  Form: TransactionForm,
};

/** Вид операции — одна вкладка страницы «Операции». Новый вид — новая строка таблицы `OPERATION_KINDS`. */
export interface OperationKind {
  key: string;
  label: string;
  Panel: ComponentType;
}

function transactionPanel(kind: TransactionKind): ComponentType {
  return function TransactionPanel() {
    return createElement(OperationsTab, { kind });
  };
}

export const OPERATION_KINDS: readonly OperationKind[] = [
  { key: "expense", label: "Расход", Panel: transactionPanel(EXPENSE_KIND) },
  { key: "topup", label: "Пополнение", Panel: transactionPanel(TOPUP_KIND) },
  { key: "transfer", label: "Перевод", Panel: TransfersTab },
];

export const DEFAULT_OPERATION_KIND = OPERATION_KINDS[0]!;

export function findOperationKind(key: string | null): OperationKind {
  return OPERATION_KINDS.find((kind) => kind.key === key) ?? DEFAULT_OPERATION_KIND;
}

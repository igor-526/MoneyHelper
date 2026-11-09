import { CompactPagination } from "./CompactPagination";
import { Button, Flex, Spin } from "antd";
import { useMemo, useState } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { WalletRateCard } from "@/features/wallets/WalletRateCard";
import { EmptyState, toLocalDateTime, useCurrencies, useIsMobile } from "@/shared/ui";
import type { Transaction } from "./Transaction";
import type { OperationFiltersState } from "./operationFilters";
import type { TransactionKind } from "./operationKinds";
import { TransactionCard } from "./TransactionCard";
import { DEFAULT_PAGE_SIZE } from "./useTransactions";

interface FormState {
  open: boolean;
  transaction?: Transaction;
}

export interface OperationsTabProps {
  kind: TransactionKind;
  filters: OperationFiltersState;
}

/** Содержимое одной вкладки: курс, список, пагинация и форма вида операции; фильтры приходят со страницы. */
export function OperationsTab({ kind, filters }: OperationsTabProps) {
  const [page, setPage] = useState(1); // 1-based, antd Pagination
  const [pageFilters, setPageFilters] = useState(filters);
  if (pageFilters !== filters) {
    setPageFilters(filters);
    setPage(1); // любая смена фильтров сбрасывает пагинацию на первую страницу
  }
  const [formState, setFormState] = useState<FormState>({ open: false });
  const isMobile = useIsMobile();

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(kind.categoryType);
  const { data: currencies = [] } = useCurrencies();

  const dateFrom = filters.dateRange
    ? toLocalDateTime(filters.dateRange[0].startOf("day"))
    : undefined;
  const dateTo = filters.dateRange ? toLocalDateTime(filters.dateRange[1].endOf("day")) : undefined;

  const listQuery = kind.useList(
    {
      walletIds: filters.walletIds,
      categoryIds: filters.categoryIds,
      commentQuery: filters.commentQuery,
      dateFrom,
      dateTo,
    },
    { offset: (page - 1) * DEFAULT_PAGE_SIZE, limit: DEFAULT_PAGE_SIZE },
  );

  const walletNameById = useMemo(
    () => new Map(wallets.map((wallet) => [wallet.id, wallet.name])),
    [wallets],
  );
  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );
  const currencyCodeById = useMemo(
    () => new Map(currencies.map((currency) => [currency.id, currency.code])),
    [currencies],
  );
  const selectedWalletId = filters.walletIds?.length === 1 ? filters.walletIds[0] : undefined;
  const selectedWallet = wallets.find((wallet) => wallet.id === selectedWalletId);

  const openCreate = () => setFormState({ open: true });
  const openEdit = (transaction: Transaction) => setFormState({ open: true, transaction });
  const closeForm = () => setFormState({ open: false });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;

  return (
    <Flex vertical gap={16}>
      {selectedWallet !== undefined ? (
        <WalletRateCard wallet={selectedWallet} currencyCodeById={currencyCodeById} />
      ) : null}
      {listQuery.isPending ? (
        <Spin />
      ) : items.length === 0 ? (
        <EmptyState
          icon="banknote"
          title={kind.emptyTitle}
          action={{ label: kind.createLabel, onClick: openCreate }}
        />
      ) : (
        <>
          <Button
            type="primary"
            block={isMobile}
            style={{ alignSelf: "flex-start" }}
            onClick={openCreate}
          >
            Добавить
          </Button>
          <Flex vertical gap={8}>
            {items.map((transaction) => {
              const category = categoryById.get(transaction.category_id);
              return (
                <TransactionCard
                  key={transaction.id}
                  transaction={transaction}
                  walletName={walletNameById.get(transaction.wallet_id)}
                  category={category && { name: category.name, icon: category.icon }}
                  currencyCodeById={currencyCodeById}
                  onEdit={openEdit}
                />
              );
            })}
          </Flex>
          <CompactPagination
            current={page}
            total={Math.ceil(total / DEFAULT_PAGE_SIZE)}
            onChange={setPage}
          />
        </>
      )}
      <kind.Form open={formState.open} transaction={formState.transaction} onClose={closeForm} />
    </Flex>
  );
}

import { Button, DatePicker, Flex, Pagination, Select, Spin } from "antd";
import type { Dayjs } from "dayjs";
import { useMemo, useState } from "react";
import { useCategories } from "@/features/categories/useCategories";
import { useWallets } from "@/features/wallets/useWallets";
import { WalletRateCard } from "@/features/wallets/WalletRateCard";
import { EmptyState, useCurrencies, useIsMobile } from "@/shared/ui";
import type { Transaction } from "./Transaction";
import type { TransactionKind } from "./operationKinds";
import { TransactionCard } from "./TransactionCard";
import { DEFAULT_PAGE_SIZE } from "./useTransactions";
import { WalletBalanceCard } from "./WalletBalanceCard";

const ALL_WALLETS = "all";
const ALL_CATEGORIES = "all";

interface FiltersState {
  walletId: string | undefined; // undefined = «Все кошельки»
  categoryId: string | undefined; // undefined = «Все категории»
  dateRange: [Dayjs, Dayjs] | null; // null = без фильтра
}

interface FormState {
  open: boolean;
  transaction?: Transaction;
}

export interface OperationsTabProps {
  kind: TransactionKind;
}

/** Содержимое одной вкладки: фильтры, баланс/курс, список, пагинация и форма вида операции. */
export function OperationsTab({ kind }: OperationsTabProps) {
  const [filters, setFilters] = useState<FiltersState>({
    walletId: undefined,
    categoryId: undefined,
    dateRange: null,
  });
  const [page, setPage] = useState(1); // 1-based, antd Pagination
  const [formState, setFormState] = useState<FormState>({ open: false });
  const isMobile = useIsMobile();

  const { data: wallets = [] } = useWallets();
  const { data: categories = [] } = useCategories(kind.categoryType);
  const { data: currencies = [] } = useCurrencies();

  const dateFrom = filters.dateRange?.[0].startOf("day").toISOString();
  const dateTo = filters.dateRange?.[1].endOf("day").toISOString();

  const listQuery = kind.useList(
    { walletId: filters.walletId, categoryId: filters.categoryId, dateFrom, dateTo },
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
  const selectedWallet = wallets.find((wallet) => wallet.id === filters.walletId);

  const updateFilters = (patch: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1); // любая смена фильтра сбрасывает пагинацию на первую страницу
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    updateFilters({ dateRange: dates && dates[0] && dates[1] ? [dates[0], dates[1]] : null });
  };

  const openCreate = () => setFormState({ open: true });
  const openEdit = (transaction: Transaction) => setFormState({ open: true, transaction });
  const closeForm = () => setFormState({ open: false });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;

  return (
    <Flex vertical gap={16}>
      <Flex vertical gap={12}>
        <Select
          aria-label="Кошелёк"
          value={filters.walletId ?? ALL_WALLETS}
          options={[
            { value: ALL_WALLETS, label: "Все кошельки" },
            ...wallets.map((wallet) => ({ value: wallet.id, label: wallet.name })),
          ]}
          onChange={(value) =>
            updateFilters({ walletId: value === ALL_WALLETS ? undefined : value })
          }
        />
        <Select
          aria-label="Категория"
          value={filters.categoryId ?? ALL_CATEGORIES}
          options={[
            { value: ALL_CATEGORIES, label: "Все категории" },
            ...categories.map((category) => ({ value: category.id, label: category.name })),
          ]}
          onChange={(value) =>
            updateFilters({ categoryId: value === ALL_CATEGORIES ? undefined : value })
          }
        />
        <DatePicker.RangePicker
          aria-label="Диапазон дат"
          placeholder={["Дата от", "Дата до"]}
          value={filters.dateRange}
          onChange={handleDateRangeChange}
          allowClear
        />
      </Flex>
      {filters.walletId !== undefined ? (
        <WalletBalanceCard walletId={filters.walletId} currencyCodeById={currencyCodeById} />
      ) : null}
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
          <Flex vertical gap={12}>
            {items.map((transaction) => {
              const category = categoryById.get(transaction.category_id);
              return (
                <TransactionCard
                  key={transaction.id}
                  transaction={transaction}
                  walletName={walletNameById.get(transaction.wallet_id)}
                  category={category && { name: category.name, icon: category.icon }}
                  currencyCodeById={currencyCodeById}
                  kind={kind}
                  onEdit={openEdit}
                />
              );
            })}
          </Flex>
          <Pagination
            current={page}
            pageSize={DEFAULT_PAGE_SIZE}
            total={total}
            onChange={setPage}
            showSizeChanger={false}
          />
        </>
      )}
      <kind.Form open={formState.open} transaction={formState.transaction} onClose={closeForm} />
    </Flex>
  );
}

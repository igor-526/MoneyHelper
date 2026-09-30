import {
  Button,
  DatePicker,
  Dropdown,
  Flex,
  Pagination,
  Segmented,
  Select,
  Spin,
  Typography,
} from "antd";
import type { Dayjs } from "dayjs";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Category, CategoryType } from "@/features/categories/Category";
import { useCategories } from "@/features/categories/useCategories";
import type { Wallet } from "@/features/wallets/Wallet";
import { useWallets } from "@/features/wallets/useWallets";
import { EmptyState, useCurrencies, useIsMobile } from "@/shared/ui";
import type { Currency } from "@/shared/ui";
import type { Transaction } from "./Transaction";
import { TopupForm } from "./TopupForm";
import { TransactionCard } from "./TransactionCard";
import { TransactionForm } from "./TransactionForm";
import { DEFAULT_PAGE_SIZE, useTransactions } from "./useTransactions";
import { WalletBalanceCard } from "./WalletBalanceCard";

const ALL_WALLETS = "all";
const ALL_CATEGORIES = "all";
type TypeFilter = "all" | CategoryType;
type CreateMenuKey = "transaction" | "topup" | "transfer";

const CREATE_MENU_ITEMS = [
  { key: "transaction", label: "Доход/расход" },
  { key: "topup", label: "Пополнение" },
  { key: "transfer", label: "Перевод" },
];

interface FiltersState {
  walletId: string | undefined; // undefined = «Все кошельки»
  categoryId: string | undefined; // undefined = «Все категории»
  type: TypeFilter; // "all" = без фильтра
  dateRange: [Dayjs, Dayjs] | null; // null = без фильтра
}

/**
 * Локальная копия таблицы из `CategoriesPage` (015), не импорт из `features/categories` — тот же принцип, что и
 * `TYPE_TAG` в `TransactionCard`: избежание кросс-фичевой связанности важнее трёх повторяющихся строк.
 */
const TYPE_FILTER_OPTIONS: { label: string; value: TypeFilter }[] = [
  { label: "Все", value: "all" },
  { label: "Доход", value: "income" },
  { label: "Расход", value: "expense" },
];

interface FormState {
  open: boolean;
  transaction?: Transaction;
}

export function TransactionsPage() {
  const [filters, setFilters] = useState<FiltersState>({
    walletId: undefined,
    categoryId: undefined,
    type: "all",
    dateRange: null,
  });
  const [page, setPage] = useState(1); // 1-based, antd Pagination
  const [formState, setFormState] = useState<FormState>({ open: false });
  const [topupFormOpen, setTopupFormOpen] = useState(false);
  const isMobile = useIsMobile();
  const navigate = useNavigate();

  const { data: wallets = [] } = useWallets();
  const { data: allCategories = [] } = useCategories(undefined);
  const { data: currencies = [] } = useCurrencies();

  const dateFrom = filters.dateRange?.[0].startOf("day").toISOString();
  const dateTo = filters.dateRange?.[1].endOf("day").toISOString();
  const offset = (page - 1) * DEFAULT_PAGE_SIZE;

  const transactionsQuery = useTransactions(
    {
      walletId: filters.walletId,
      categoryId: filters.categoryId,
      type: filters.type === "all" ? undefined : filters.type,
      dateFrom,
      dateTo,
    },
    { offset, limit: DEFAULT_PAGE_SIZE },
  );

  const walletNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const wallet of wallets as Wallet[]) map.set(wallet.id, wallet.name);
    return map;
  }, [wallets]);

  const categoryById = useMemo(() => {
    const map = new Map<string, Category>();
    for (const category of allCategories as Category[]) map.set(category.id, category);
    return map;
  }, [allCategories]);

  const currencyCodeById = useMemo(() => {
    const map = new Map<string, string>();
    for (const currency of currencies as Currency[]) map.set(currency.id, currency.code);
    return map;
  }, [currencies]);

  const updateFilters = (patch: Partial<FiltersState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1); // любая смена фильтра сбрасывает пагинацию на первую страницу
  };

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      updateFilters({ dateRange: [dates[0], dates[1]] });
    } else {
      updateFilters({ dateRange: null });
    }
  };

  const openCreate = () => setFormState({ open: true, transaction: undefined });
  const openEdit = (transaction: Transaction) => setFormState({ open: true, transaction });
  const closeForm = () => setFormState({ open: false });
  const closeTopupForm = () => setTopupFormOpen(false);

  const handleCreateMenuClick = ({ key }: { key: string }) => {
    const menuKey = key as CreateMenuKey;
    if (menuKey === "transaction") openCreate();
    else if (menuKey === "topup") setTopupFormOpen(true);
    else navigate("/transfers");
  };

  const items = transactionsQuery.data?.items ?? [];
  const total = transactionsQuery.data?.total ?? 0;

  return (
    <Flex vertical gap={16}>
      <Flex justify="space-between" align="center">
        <Typography.Title level={3} style={{ margin: 0 }}>
          Операции
        </Typography.Title>
        <Typography.Link onClick={() => navigate("/transfers")}>Переводы</Typography.Link>
      </Flex>
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
            ...allCategories.map((category) => ({ value: category.id, label: category.name })),
          ]}
          onChange={(value) =>
            updateFilters({ categoryId: value === ALL_CATEGORIES ? undefined : value })
          }
        />
        <Segmented
          aria-label="Тип"
          options={TYPE_FILTER_OPTIONS}
          value={filters.type}
          onChange={(value) => updateFilters({ type: value as TypeFilter })}
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
      {transactionsQuery.isPending ? (
        <Spin />
      ) : items.length === 0 ? (
        <EmptyState
          icon="banknote"
          title="Операций пока нет"
          action={{ label: "Создать операцию", onClick: openCreate }}
        />
      ) : (
        <>
          <Dropdown menu={{ items: CREATE_MENU_ITEMS, onClick: handleCreateMenuClick }}>
            <Button type="primary" block={isMobile} style={{ alignSelf: "flex-start" }}>
              Добавить
            </Button>
          </Dropdown>
          <Flex vertical gap={12}>
            {items.map((transaction) => {
              const category = categoryById.get(transaction.category_id);
              return (
                <TransactionCard
                  key={transaction.id}
                  transaction={transaction}
                  walletName={walletNameById.get(transaction.wallet_id)}
                  category={
                    category
                      ? { name: category.name, icon: category.icon, type: category.type }
                      : undefined
                  }
                  currencyCodeById={currencyCodeById}
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
      <TransactionForm
        open={formState.open}
        transaction={formState.transaction}
        onClose={closeForm}
      />
      <TopupForm open={topupFormOpen} onClose={closeTopupForm} />
    </Flex>
  );
}

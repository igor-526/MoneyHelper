import { Button, DatePicker, Flex, Pagination, Select, Spin, Typography } from "antd";
import type { Dayjs } from "dayjs";
import { useMemo, useState } from "react";
import { useWallets } from "@/features/wallets/useWallets";
import { EmptyState, useCurrencies, useIsMobile } from "@/shared/ui";
import { TransferCard } from "./TransferCard";
import { TransferForm } from "./TransferForm";
import type { Transfer } from "./Transfer";
import { DEFAULT_PAGE_SIZE, useTransfers } from "./useTransfers";

const ALL_WALLETS = "all";

interface FiltersState {
  walletId: string | undefined; // undefined = «Все кошельки»
  dateRange: [Dayjs, Dayjs] | null; // null = без фильтра
}

interface FormState {
  open: boolean;
  transfer?: Transfer;
}

export function TransfersPage() {
  const [filters, setFilters] = useState<FiltersState>({ walletId: undefined, dateRange: null });
  const [page, setPage] = useState(1); // 1-based, antd Pagination
  const [formState, setFormState] = useState<FormState>({ open: false });
  const isMobile = useIsMobile();

  const { data: wallets = [] } = useWallets();
  const { data: currencies = [] } = useCurrencies();

  const dateFrom = filters.dateRange?.[0].startOf("day").toISOString();
  const dateTo = filters.dateRange?.[1].endOf("day").toISOString();
  const offset = (page - 1) * DEFAULT_PAGE_SIZE;

  const transfersQuery = useTransfers(
    { walletId: filters.walletId, dateFrom, dateTo },
    { offset, limit: DEFAULT_PAGE_SIZE },
  );

  const walletNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const wallet of wallets) map.set(wallet.id, wallet.name);
    return map;
  }, [wallets]);

  const currencyCodeById = useMemo(() => {
    const map = new Map<string, string>();
    for (const currency of currencies) map.set(currency.id, currency.code);
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

  const openCreate = () => setFormState({ open: true, transfer: undefined });
  const openEdit = (transfer: Transfer) => setFormState({ open: true, transfer });
  const closeForm = () => setFormState({ open: false });

  const items = transfersQuery.data?.items ?? [];
  const total = transfersQuery.data?.total ?? 0;

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Переводы
      </Typography.Title>
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
        <DatePicker.RangePicker
          aria-label="Диапазон дат"
          placeholder={["Дата от", "Дата до"]}
          value={filters.dateRange}
          onChange={handleDateRangeChange}
          allowClear
        />
      </Flex>
      {transfersQuery.isPending ? (
        <Spin />
      ) : items.length === 0 ? (
        <EmptyState
          icon="wallet"
          title="Переводов пока нет"
          action={{ label: "Создать перевод", onClick: openCreate }}
        />
      ) : (
        <>
          <Button
            type="primary"
            block={isMobile}
            onClick={openCreate}
            style={{ alignSelf: "flex-start" }}
          >
            Создать перевод
          </Button>
          <Flex vertical gap={12}>
            {items.map((transfer) => (
              <TransferCard
                key={transfer.id}
                transfer={transfer}
                fromWalletName={walletNameById.get(transfer.from_wallet_id)}
                toWalletName={walletNameById.get(transfer.to_wallet_id)}
                currencyCode={currencyCodeById.get(transfer.currency_id)}
                onEdit={openEdit}
              />
            ))}
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
      <TransferForm open={formState.open} transfer={formState.transfer} onClose={closeForm} />
    </Flex>
  );
}

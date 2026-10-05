import { Button, Flex, Pagination, Spin } from "antd";
import { useMemo, useState } from "react";
import type { OperationFiltersState } from "@/features/transactions/operationFilters";
import { useWallets } from "@/features/wallets/useWallets";
import { EmptyState, useCurrencies, useIsMobile } from "@/shared/ui";
import { TransferCard } from "./TransferCard";
import { TransferForm } from "./TransferForm";
import type { Transfer } from "./Transfer";
import { DEFAULT_PAGE_SIZE, useTransfers } from "./useTransfers";

interface FormState {
  open: boolean;
  transfer?: Transfer;
}

/** Содержимое вкладки «Перевод» страницы «Операции»: список, пагинация и форма переводов; фильтры приходят со страницы. */
export function TransfersTab({ filters }: { filters: OperationFiltersState }) {
  const [page, setPage] = useState(1); // 1-based, antd Pagination
  const [pageFilters, setPageFilters] = useState(filters);
  if (pageFilters !== filters) {
    setPageFilters(filters);
    setPage(1); // любая смена фильтров сбрасывает пагинацию на первую страницу
  }
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

  const walletById = useMemo(
    () => new Map(wallets.map((wallet) => [wallet.id, wallet])),
    [wallets],
  );

  const currencyCodeById = useMemo(() => {
    const map = new Map<string, string>();
    for (const currency of currencies) map.set(currency.id, currency.code);
    return map;
  }, [currencies]);

  const openCreate = () => setFormState({ open: true, transfer: undefined });
  const openEdit = (transfer: Transfer) => setFormState({ open: true, transfer });
  const closeForm = () => setFormState({ open: false });

  const items = transfersQuery.data?.items ?? [];
  const total = transfersQuery.data?.total ?? 0;

  return (
    <Flex vertical gap={16}>
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
          <Flex vertical gap={8}>
            {items.map((transfer) => (
              <TransferCard
                key={transfer.id}
                transfer={transfer}
                fromWalletName={walletById.get(transfer.from_wallet_id)?.name}
                toWalletName={walletById.get(transfer.to_wallet_id)?.name}
                currencyCode={currencyCodeById.get(
                  walletById.get(transfer.from_wallet_id)?.currency_id ?? "",
                )}
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

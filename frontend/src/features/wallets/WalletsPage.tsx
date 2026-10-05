import { Button, Flex, Spin, Typography } from "antd";
import { useMemo, useState } from "react";
import { EmptyState, useCurrencies, useIsMobile } from "@/shared/ui";
import type { Currency } from "@/shared/ui";
import type { Wallet } from "./Wallet";
import { WalletCard } from "./WalletCard";
import { WalletForm } from "./WalletForm";
import { useWallets } from "./useWallets";

interface FormState {
  open: boolean;
  wallet?: Wallet;
}

export function WalletsPage() {
  const walletsQuery = useWallets();
  const currenciesQuery = useCurrencies();
  const isMobile = useIsMobile();
  const [formState, setFormState] = useState<FormState>({ open: false });

  const currencyById = useMemo(() => {
    const map = new Map<string, Currency>();
    for (const currency of currenciesQuery.data ?? []) {
      map.set(currency.id, currency);
    }
    return map;
  }, [currenciesQuery.data]);

  const openCreate = () => setFormState({ open: true, wallet: undefined });
  const openEdit = (wallet: Wallet) => setFormState({ open: true, wallet });
  const closeForm = () => setFormState({ open: false });

  if (walletsQuery.isPending) {
    return <Spin />;
  }

  const wallets = walletsQuery.data ?? [];

  return (
    <Flex vertical gap={16}>
      {wallets.length === 0 ? (
        <EmptyState
          icon="wallet"
          title="Кошельков пока нет"
          action={{ label: "Создать кошелёк", onClick: openCreate }}
        />
      ) : (
        <>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Кошельки
          </Typography.Title>
          <Button
            type="primary"
            block={isMobile}
            onClick={openCreate}
            style={{ alignSelf: "flex-start" }}
          >
            Создать кошелёк
          </Button>
          <Flex vertical gap={12}>
            {wallets.map((wallet) => (
              <WalletCard
                key={wallet.id}
                wallet={wallet}
                currencyCode={currencyById.get(wallet.currency_id)?.code}
                onEdit={openEdit}
              />
            ))}
          </Flex>
        </>
      )}
      <WalletForm open={formState.open} wallet={formState.wallet} onClose={closeForm} />
    </Flex>
  );
}

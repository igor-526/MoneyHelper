import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WalletBalanceCard } from "@/features/transactions/WalletBalanceCard";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { TransferForm } from "./TransferForm";

const TEST_WORKSPACE_ID = "workspace-1";

/**
 * Проверяет требование «Мутация перевода обновляет кэш балансов затронутых кошельков» (specs/frontend-transfers):
 * успешная мутация перевода (создание/редактирование/удаление) инвалидирует `["wallet-balances"]` — если
 * `WalletBalanceCard` (`features/transactions`) открыта на другом экране приложения (например, «Операции»), она
 * перезапрашивает баланс без перезагрузки страницы. `WalletBalanceCard` и `TransferForm` рендерятся рядом в
 * одном дереве, разделяя один `QueryClient` и `ApiClient` — так же, как это происходит в реальном приложении,
 * когда экраны «Операции» и «Переводы» используют общий кэш TanStack Query.
 */

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_ids: ["cur1"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_ids: ["cur1"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

const CURRENCIES = [{ id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 }];

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`) return page(WALLETS);
    if (request.path === "/api/currencies") return page(CURRENCIES);
    return handler(request);
  };
}

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(withFixtures(handler));
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>
          <ToastProvider>{children}</ToastProvider>
        </WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

function formControl(labelText: string): HTMLElement {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  return within(formItem).getByRole("combobox");
}

/**
 * "Откуда"/"Куда" делят один и тот же список кошельков и переиспользуют DOM-контейнер выпадающего списка между
 * открытиями (см. подробный комментарий в `TransferForm.test.tsx`) — ищем контейнер, не находящийся в процессе
 * закрытия/подготовки к открытию.
 */
function visibleDropdownList(): HTMLElement {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>(".ant-select-dropdown-list"));
  const visible = nodes.find((node) => {
    const dropdown = node.closest<HTMLElement>(".ant-select-dropdown");
    if (!dropdown) return false;
    return !dropdown.className.includes("leave") && !dropdown.className.includes("prepare");
  });
  if (!visible) throw new Error("Видимый выпадающий список ещё не готов");
  return visible;
}

async function selectOption(labelText: string, optionLabel: string) {
  await userEvent.click(formControl(labelText));
  const dropdown = await waitFor(() => visibleDropdownList());
  await userEvent.click(within(dropdown).getByText(optionLabel));
}

describe("инвалидация баланса кошелька мутациями переводов", () => {
  it("успешное создание перевода перезапрашивает открытую WalletBalanceCard", async () => {
    const CREATED = {
      id: "1",
      from_wallet_id: "w1",
      to_wallet_id: "w2",
      currency_id: "cur1",
      amount: "10",
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup((request) => {
      if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/transfers`) return CREATED;
      if (request.path.endsWith("/balances")) return [{ currency_id: "cur1", balance: "0.00" }];
      return undefined;
    });

    render(
      <>
        <WalletBalanceCard walletId="w1" currencyCodeById={new Map([["cur1", "USD"]])} />
        <TransferForm open onClose={() => {}} />
      </>,
      { wrapper },
    );

    await screen.findByText("USD: 0.00");
    await waitFor(() =>
      expect(api.requests.filter((r) => r.path.endsWith("/balances"))).toHaveLength(1),
    );

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Карта");
    await selectOption("Валюта", "USD — Доллар США");
    await userEvent.type(screen.getByLabelText("Сумма"), "10");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() =>
      expect(api.requests.filter((r) => r.path.endsWith("/balances")).length).toBeGreaterThan(1),
    );
  });
});

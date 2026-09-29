import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { setMedia } from "@/test/matchMedia";
import type { Wallet } from "./Wallet";
import { WalletForm } from "./WalletForm";

const CURRENCIES_PAGE = {
  items: [
    { id: "1", code: "USD", name: "Доллар США", decimal_places: 2 },
    { id: "2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

const WALLET: Wallet = {
  id: "5",
  name: "Наличные",
  icon: "wallet",
  currency_ids: ["1"],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

function withCurrencies(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/currencies") return CURRENCIES_PAGE;
    return handler(request);
  };
}

/** Настоящий `ToastProvider`, чтобы проверять видимые уведомления, как использует их компонент. */
function setup(handler: FakeHandler) {
  const api = new FakeApiClient(withCurrencies(handler));
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

async function selectIcon(name: string) {
  await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));
  await userEvent.click(await screen.findByRole("option", { name }));
}

async function selectCurrency(label: string) {
  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(await screen.findByText(label));
}

describe("WalletForm", () => {
  it("создание: успех добавляет кошелёк и закрывает форму", async () => {
    const CREATED = {
      id: "9",
      name: "Новый кошелёк",
      icon: "wallet",
      currency_ids: ["1"],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<WalletForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Новый кошелёк");
    await selectIcon("wallet");
    await selectCurrency("USD — Доллар США");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "POST",
      path: "/api/wallets",
      body: { name: "Новый кошелёк", icon: "wallet", currency_ids: ["1"] },
    });
    expect(await screen.findByText("Кошелёк создан")).toBeInTheDocument();
  });

  it("редактирование: поля предзаполнены, успех обновляет кошелёк", async () => {
    const UPDATED = { ...WALLET, name: "Обновлённый" };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<WalletForm open wallet={WALLET} onClose={onClose} />, { wrapper });

    expect(screen.getByLabelText("Название")).toHaveValue("Наличные");
    expect(document.querySelector('[data-icon="wallet"]')).toBeInTheDocument();
    expect(await screen.findByText("USD — Доллар США")).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Название"));
    await userEvent.type(screen.getByLabelText("Название"), "Обновлённый");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: "/api/wallets/5",
      body: { name: "Обновлённый", icon: "wallet", currency_ids: ["1"] },
    });
    expect(await screen.findByText("Кошелёк обновлён")).toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["Название уже используется"] },
      });
    });
    const onClose = vi.fn();
    render(<WalletForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Дубликат");
    await selectIcon("wallet");
    await selectCurrency("USD — Доллар США");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Название уже используется")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => WALLET);
    render(<WalletForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => WALLET);
    render(<WalletForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});

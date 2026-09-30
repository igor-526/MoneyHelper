import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import type { Transfer } from "./Transfer";
import { TransferForm } from "./TransferForm";

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_ids: ["cur1", "cur2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "w2",
    name: "Карта",
    icon: "credit-card",
    currency_ids: ["cur2"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "w3",
    name: "Крипто",
    icon: "coins",
    currency_ids: ["cur3"],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
];

const CURRENCIES = [
  { id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 },
  { id: "cur2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  { id: "cur3", code: "BTC", name: "Биткоин", decimal_places: 8 },
];

const TRANSFER: Transfer = {
  id: "t1",
  from_wallet_id: "w1",
  to_wallet_id: "w2",
  currency_id: "cur2",
  amount: "25.00",
  occurred_at: "2026-02-01T10:00:00Z",
  created_at: "2026-02-01T10:00:00Z",
  updated_at: null,
};

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

function withFixtures(handler: FakeHandler): FakeHandler {
  return (request) => {
    if (request.path === "/api/wallets") return page(WALLETS);
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
        <ToastProvider>{children}</ToastProvider>
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
 * Каждый antd `Select` переиспользует свой DOM-контейнер выпадающего списка между открытиями (не пересоздаёт
 * его), поэтому порядок контейнеров в DOM соответствует порядку, в котором поля были открыты первый раз, а не
 * тому, какое поле открыто сейчас — «последний в DOM» не значит «видимый сейчас». Ищем контейнер, который не в
 * процессе закрытия (`*-leave`) и не в фазе подготовки открытия (`*-prepare`, когда `pointer-events` ещё
 * `none`) — `waitFor` повторяет проверку, пока анимация открытия не перейдёт в активную фазу.
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

/**
 * `null`, если поле сброшено — как обычным пустым `Select`, так и (для «Валюта» без общей валюты кошельков)
 * заменой на предупреждающий текст, у которого combobox нет вовсе.
 */
function selectedLabel(labelText: string): string | null {
  const label = screen.getByText(labelText);
  const formItem = label.closest(".ant-form-item") as HTMLElement;
  const combobox = within(formItem).queryByRole("combobox");
  if (!combobox) return null;
  const content = combobox.closest(".ant-select-content");
  return content?.getAttribute("title") ?? null;
}

async function fillMinimalForm() {
  await selectOption("Откуда", "Наличные");
  await selectOption("Куда", "Карта");
  await selectOption("Валюта", "RUB — Российский рубль");
  await userEvent.type(screen.getByLabelText("Сумма"), "10");
}

describe("TransferForm", () => {
  it("целевой кошелёк исключает исходный из опций", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await userEvent.click(formControl("Куда"));
    const dropdown = await waitFor(() => visibleDropdownList());

    expect(within(dropdown).queryByText("Наличные")).not.toBeInTheDocument();
    expect(within(dropdown).getByText("Карта")).toBeInTheDocument();
    expect(within(dropdown).getByText("Крипто")).toBeInTheDocument();
  });

  it("смена исходного кошелька на совпадающий с целевым сбрасывает целевой", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Карта");
    expect(selectedLabel("Куда")).toBe("Карта");

    await selectOption("Откуда", "Карта");

    expect(selectedLabel("Куда")).toBeNull();
  });

  it("валюта ограничена пересечением наборов валют двух кошельков", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Карта");
    await userEvent.click(formControl("Валюта"));

    expect(await screen.findByText("RUB — Российский рубль")).toBeInTheDocument();
    expect(screen.queryByText("USD — Доллар США")).not.toBeInTheDocument();
  });

  it("смена целевого кошелька сбрасывает выбранную валюту", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Карта");
    await selectOption("Валюта", "RUB — Российский рубль");
    expect(selectedLabel("Валюта")).toBe("RUB — Российский рубль");

    await selectOption("Куда", "Крипто");

    expect(selectedLabel("Валюта")).toBeNull();
  });

  it("смена исходного кошелька сбрасывает выбранную валюту", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Карта");
    await selectOption("Валюта", "RUB — Российский рубль");
    expect(selectedLabel("Валюта")).toBe("RUB — Российский рубль");

    await selectOption("Откуда", "Крипто");

    expect(selectedLabel("Валюта")).toBeNull();
  });

  it("отсутствие общей валюты показывает предупреждающий текст вместо поля выбора", async () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    await selectOption("Откуда", "Наличные");
    await selectOption("Куда", "Крипто");

    expect(await screen.findByText("У этих кошельков нет общей валюты")).toBeInTheDocument();
    // Поле выбора (combobox) валюты не рендерится — только предупреждающий текст под той же подписью.
    const label = screen.getByText("Валюта");
    const formItem = label.closest(".ant-form-item") as HTMLElement;
    expect(within(formItem).queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("успешное создание", async () => {
    const CREATED = {
      id: "9",
      from_wallet_id: "w1",
      to_wallet_id: "w2",
      currency_id: "cur2",
      amount: "10",
      occurred_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<TransferForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const request = api.requests.find((r) => r.method === "POST" && r.path === "/api/transfers");
    expect(request).toMatchObject({
      body: { from_wallet_id: "w1", to_wallet_id: "w2", currency_id: "cur2", amount: "10" },
    });
    expect(await screen.findByText("Перевод создан")).toBeInTheDocument();
  });

  it("успешное редактирование с предзаполнением полей", async () => {
    const UPDATED = { ...TRANSFER, amount: "30.00" };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<TransferForm open transfer={TRANSFER} onClose={onClose} />, { wrapper });

    await waitFor(() => expect(selectedLabel("Откуда")).toBe("Наличные"));
    expect(selectedLabel("Куда")).toBe("Карта");
    expect(selectedLabel("Валюта")).toBe("RUB — Российский рубль");
    expect(screen.getByLabelText("Сумма")).toHaveValue("25.00");

    await userEvent.clear(screen.getByLabelText("Сумма"));
    await userEvent.type(screen.getByLabelText("Сумма"), "30.00");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: "/api/transfers/t1",
      body: { from_wallet_id: "w1", to_wallet_id: "w2", currency_id: "cur2", amount: "30.00" },
    });
    expect(await screen.findByText("Перевод обновлён")).toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { amount: ["Сумма должна быть положительной"] },
      });
    });
    const onClose = vi.fn();
    render(<TransferForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Сумма должна быть положительной")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("текстовая ошибка бизнес-правила backend показывается toast без падения формы", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        detail: "Исходный и целевой кошелёк совпадают",
      });
    });
    const onClose = vi.fn();
    render(<TransferForm open onClose={onClose} />, { wrapper });

    await fillMinimalForm();
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(
      await screen.findByText("Проверьте заполнение формы: Исходный и целевой кошелёк совпадают"),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => ({}));
    render(<TransferForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});

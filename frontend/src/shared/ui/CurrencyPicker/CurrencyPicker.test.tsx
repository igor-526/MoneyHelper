import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { CurrencyPicker } from "./CurrencyPicker";

const CURRENCIES_PAGE = {
  items: [
    { id: "1", code: "USD", name: "Доллар США", decimal_places: 2 },
    { id: "2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>{children}</ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

function SingleHarness({ onChange }: { onChange: (value: string | undefined) => void }) {
  const [value, setValue] = useState<string | undefined>(undefined);
  return (
    <CurrencyPicker
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

function MultipleHarness({ onChange }: { onChange: (value: string[]) => void }) {
  const [value, setValue] = useState<string[]>([]);
  return (
    <CurrencyPicker
      multiple
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

describe("CurrencyPicker", () => {
  it("отображает валюты по code и name", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    render(<CurrencyPicker value={undefined} onChange={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByText("USD — Доллар США")).toBeInTheDocument();
    expect(screen.getByText("RUB — Российский рубль")).toBeInTheDocument();
  });

  it("одиночный выбор: onChange вызывается с id строкой", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    const onChange = vi.fn();
    render(<SingleHarness onChange={onChange} />, { wrapper });

    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(await screen.findByText("USD — Доллар США"));

    expect(onChange).toHaveBeenCalledWith("1");
  });

  it("множественный выбор: onChange накапливает id всех выбранных валют", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    const onChange = vi.fn();
    render(<MultipleHarness onChange={onChange} />, { wrapper });

    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(await screen.findByText("USD — Доллар США"));
    await userEvent.click(await screen.findByText("RUB — Российский рубль"));

    expect(onChange).toHaveBeenLastCalledWith(["1", "2"]);
  });

  it("показывает состояние загрузки, пока ответ не получен", () => {
    const { wrapper } = setup(() => new Promise(() => {}));
    const { container } = render(<CurrencyPicker value={undefined} onChange={vi.fn()} />, {
      wrapper,
    });

    expect(container.querySelector(".anticon-loading")).toBeInTheDocument();
  });

  it("при ошибке загрузки поле недоступно с placeholder «Валюты недоступны»", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });
    render(<CurrencyPicker value={undefined} onChange={vi.fn()} placeholder="Валюта" />, {
      wrapper,
    });

    await waitFor(() => expect(screen.getByRole("combobox")).toBeDisabled());
    expect(screen.getByText("Валюты недоступны")).toBeInTheDocument();
  });

  it("без allowedIds список опций совпадает с полным списком валют", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    render(<CurrencyPicker value={undefined} onChange={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByText("USD — Доллар США")).toBeInTheDocument();
    expect(screen.getByText("RUB — Российский рубль")).toBeInTheDocument();
  });

  it("с allowedIds список опций ограничен переданными id (одиночный режим)", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    render(<CurrencyPicker value={undefined} onChange={vi.fn()} allowedIds={["1"]} />, {
      wrapper,
    });

    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByText("USD — Доллар США")).toBeInTheDocument();
    expect(screen.queryByText("RUB — Российский рубль")).not.toBeInTheDocument();
  });

  it("с allowedIds список опций ограничен переданными id (множественный режим)", async () => {
    const { wrapper } = setup(() => CURRENCIES_PAGE);
    render(<CurrencyPicker multiple value={[]} onChange={vi.fn()} allowedIds={["2"]} />, {
      wrapper,
    });

    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByText("RUB — Российский рубль")).toBeInTheDocument();
    expect(screen.queryByText("USD — Доллар США")).not.toBeInTheDocument();
  });
});

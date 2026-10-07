import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type * as SharedUi from "@/shared/ui";
import { RateMode } from "./RateMode";

const state = vi.hoisted(() => ({
  wallets: [
    {
      id: "wallet-cny",
      currency_id: "cny",
      name: "CNY",
      icon: "wallet",
      created_at: "",
      updated_at: null,
    },
  ],
  currencies: [
    { id: "rub", code: "RUB", name: "Рубль", decimalPlaces: 2 },
    { id: "cny", code: "CNY", name: "Юань", decimalPlaces: 2 },
  ],
  points: [
    { date: "2026-01-01", rate: "10.0000000000" },
    { date: "2026-01-03", rate: "14.0000000000" },
  ],
}));

vi.mock("@/features/workspaces/useCurrentWorkspace", () => ({
  useCurrentWorkspace: () => ({ currency_id: "rub" }),
}));
vi.mock("@/features/wallets/useWallets", () => ({
  useWallets: () => ({ data: state.wallets, isPending: false }),
}));
vi.mock("@/shared/ui", async (importOriginal) => ({
  ...(await importOriginal<typeof SharedUi>()),
  useCurrencies: () => ({ data: state.currencies, isPending: false }),
}));
vi.mock("./useExchangeRateHistory", () => ({
  useExchangeRateHistory: () => ({
    data: { base_currency_id: "cny", quote_currency_id: "rub", points: state.points },
    isPending: false,
  }),
}));

describe("RateMode", () => {
  beforeEach(() => {
    state.wallets = [
      {
        id: "wallet-cny",
        currency_id: "cny",
        name: "CNY",
        icon: "wallet",
        created_at: "",
        updated_at: null,
      },
    ];
    state.points = [
      { date: "2026-01-01", rate: "10.0000000000" },
      { date: "2026-01-03", rate: "14.0000000000" },
    ];
  });

  it("показывает плавный график и агрегаты выбранной валюты", () => {
    render(<RateMode range={{}} />);

    expect(screen.getByText("CNY — Юань")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "График курса CNY к RUB" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Статистика курса" })).toHaveTextContent(
      "10.0000000000 RUB за 1 CNY",
    );
    expect(screen.getByRole("table", { name: "Статистика курса" })).toHaveTextContent(
      "14.0000000000 RUB за 1 CNY",
    );
    expect(screen.getByRole("table", { name: "Статистика курса" })).toHaveTextContent(
      "12.0000000000 RUB за 1 CNY",
    );
  });

  it("показывает пустое состояние без нерублёвых валют", () => {
    state.wallets = [];

    render(<RateMode range={{}} />);

    expect(screen.getByText("Нет валют для расчёта курса к RUB")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Валюта курса" })).not.toBeInTheDocument();
  });

  it("не показывает график и агрегаты без точек", () => {
    state.points = [];

    render(<RateMode range={{}} />);

    expect(screen.getByText("Нет данных о курсе за выбранный период")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Статистика курса" })).not.toBeInTheDocument();
  });
});

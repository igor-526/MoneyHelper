import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { Wallet } from "./Wallet";
import { WalletRateCard } from "./WalletRateCard";

const TEST_WORKSPACE_ID = "workspace-1";

const CURRENCY_CODE_BY_ID = new Map([
  ["cur1", "RUB"],
  ["cur2", "CNY"],
  ["cur3", "USDT"],
]);

const MULTI_CURRENCY_WALLET: Wallet = {
  id: "w1",
  name: "Alipay",
  icon: "wallet",
  currency_ids: ["cur1", "cur2", "cur3"],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const SINGLE_CURRENCY_WALLET: Wallet = {
  ...MULTI_CURRENCY_WALLET,
  id: "w2",
  currency_ids: ["cur1"],
};

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>{children}</WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("WalletRateCard", () => {
  it("рендерит курс относительно первой по коду валюты кошелька (currency_ids[0])", async () => {
    const { api, wrapper } = setup(() => ({
      target_currency_id: "cur1",
      rates: [{ currency_id: "cur2", rate: "12.8205" }],
      unrated_currency_ids: ["cur3"],
    }));
    render(
      <WalletRateCard wallet={MULTI_CURRENCY_WALLET} currencyCodeById={CURRENCY_CODE_BY_ID} />,
      {
        wrapper,
      },
    );

    expect(await screen.findByText("1 CNY ≈ 12.8205 RUB")).toBeInTheDocument();
    expect(screen.getByText("USDT: нет данных для курса")).toBeInTheDocument();
    expect(api.requests[0]).toMatchObject({
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w1/rates`,
      query: { target_currency_id: "cur1" },
    });
  });

  it("кошелёк с одной валютой — компонент ничего не рендерит и не делает запрос", () => {
    const { api, wrapper } = setup(() => {
      throw new Error("не должно вызываться для кошелька с одной валютой");
    });
    const { container } = render(
      <WalletRateCard wallet={SINGLE_CURRENCY_WALLET} currencyCodeById={CURRENCY_CODE_BY_ID} />,
      { wrapper },
    );

    expect(container).toBeEmptyDOMElement();
    expect(api.requests).toHaveLength(0);
  });

  it("ошибка загрузки не приводит к падению компонента", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });
    const { container } = render(
      <WalletRateCard wallet={MULTI_CURRENCY_WALLET} currencyCodeById={CURRENCY_CODE_BY_ID} />,
      { wrapper },
    );

    await waitFor(() => expect(container.querySelector(".ant-spin")).not.toBeInTheDocument());
    expect(container).toBeEmptyDOMElement();
  });
});

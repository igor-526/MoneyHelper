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

const WALLET: Wallet = {
  id: "w1",
  name: "Alipay",
  icon: "wallet",
  currency_id: "cur2",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
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

function renderCard(handler: FakeHandler) {
  const { api, wrapper } = setup(handler);
  const view = render(<WalletRateCard wallet={WALLET} currencyCodeById={CURRENCY_CODE_BY_ID} />, {
    wrapper,
  });
  return { api, ...view };
}

describe("WalletRateCard", () => {
  it("рендерит курс валюты кошелька к валюте воркспейса", async () => {
    const { api } = renderCard(() => ({
      workspace_currency_id: "cur1",
      wallet_currency_id: "cur2",
      rate: "12.8205",
    }));

    expect(await screen.findByText("1 CNY ≈ 12.8205 RUB")).toBeInTheDocument();
    expect(
      screen.getByText("Среднее по пополнениям этого кошелька за всё время"),
    ).toBeInTheDocument();
    expect(api.requests[0]).toMatchObject({
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w1/rates`,
    });
    expect(api.requests[0]?.query).toBeUndefined();
  });

  it("rate === null: объясняет, что курс пока не определён", async () => {
    renderCard(() => ({
      workspace_currency_id: "cur1",
      wallet_currency_id: "cur2",
      rate: null,
    }));

    expect(
      await screen.findByText(
        "Курс пока не определён: пополните кошелёк, указав суммы в обеих валютах.",
      ),
    ).toBeInTheDocument();
  });

  it("валюты совпадают: карточка не отображается", async () => {
    const { container } = renderCard(() => ({
      workspace_currency_id: "cur1",
      wallet_currency_id: "cur1",
      rate: "1",
    }));

    await waitFor(() => expect(container.querySelector(".ant-spin")).not.toBeInTheDocument());
    expect(container).toBeEmptyDOMElement();
  });

  it("валюты совпадают и rate === null: карточка не отображается", async () => {
    const { container } = renderCard(() => ({
      workspace_currency_id: "cur1",
      wallet_currency_id: "cur1",
      rate: null,
    }));

    await waitFor(() => expect(container.querySelector(".ant-spin")).not.toBeInTheDocument());
    expect(container).toBeEmptyDOMElement();
  });

  it("ошибка загрузки не приводит к падению компонента", async () => {
    const { container } = renderCard(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    await waitFor(() => expect(container.querySelector(".ant-spin")).not.toBeInTheDocument());
    expect(container).toBeEmptyDOMElement();
  });
});

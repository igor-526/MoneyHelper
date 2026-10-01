import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { WalletBalanceCard } from "./WalletBalanceCard";

const TEST_WORKSPACE_ID = "workspace-1";

const CURRENCY_CODE_BY_ID = new Map([
  ["cur1", "USD"],
  ["cur2", "RUB"],
]);

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

describe("WalletBalanceCard", () => {
  it("рендерит список балансов по валютам, включая нулевой баланс", async () => {
    const { wrapper } = setup(() => [
      { currency_id: "cur1", balance: "150.00" },
      { currency_id: "cur2", balance: "0.00" },
    ]);
    render(<WalletBalanceCard walletId="w1" currencyCodeById={CURRENCY_CODE_BY_ID} />, {
      wrapper,
    });

    expect(await screen.findByText("USD: 150.00")).toBeInTheDocument();
    expect(screen.getByText("RUB: 0.00")).toBeInTheDocument();
  });

  it("состояние загрузки: отображается Spin", () => {
    const { wrapper } = setup(() => new Promise(() => {}));
    const { container } = render(
      <WalletBalanceCard walletId="w1" currencyCodeById={CURRENCY_CODE_BY_ID} />,
      { wrapper },
    );

    expect(container.querySelector(".ant-spin")).toBeInTheDocument();
  });

  it("ошибка загрузки не приводит к падению компонента", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });
    const { container } = render(
      <WalletBalanceCard walletId="w1" currencyCodeById={CURRENCY_CODE_BY_ID} />,
      { wrapper },
    );

    await waitFor(() => expect(container.querySelector(".ant-spin")).not.toBeInTheDocument());
    expect(container).toBeEmptyDOMElement();
  });
});

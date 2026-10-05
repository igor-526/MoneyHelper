import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useWalletRates } from "./useWalletRates";

const TEST_WORKSPACE_ID = "workspace-1";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, {
        client: api,
        children: createElement(WorkspaceContext.Provider, { value: TEST_WORKSPACE_ID, children }),
      }),
    );
  return { api, wrapper };
}

const RATES = {
  workspace_currency_id: "cur1",
  wallet_currency_id: "cur2",
  rate: "12.8205",
};

describe("useWalletRates", () => {
  it("успешная загрузка возвращает курс без маппинга", async () => {
    const { api, wrapper } = setup(() => RATES);

    const { result } = renderHook(() => useWalletRates("w1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(RATES);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w1/rates`,
    });
  });

  it("состояние ошибки", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useWalletRates("w1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

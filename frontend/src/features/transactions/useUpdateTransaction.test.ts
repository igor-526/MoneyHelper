import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { transactionsQueryKey } from "./useTransactions";
import { useUpdateTransaction } from "./useUpdateTransaction";
import { walletBalancesQueryKey } from "./useWalletBalances";

const TEST_WORKSPACE_ID = "workspace-1";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, {
        client: api,
        children: createElement(WorkspaceContext.Provider, { value: TEST_WORKSPACE_ID, children }),
      }),
    );
  return { api, toast, invalidateSpy, wrapper };
}

const VALUES = {
  wallet_id: "w1",
  category_id: "c1",
  currency_id: "cur1",
  amount: "20.00",
};
const UPDATED = {
  id: "1",
  wallet_id: "w1",
  category_id: "c1",
  legs: [{ currency_id: "cur1", amount: "20.00" }],
  occurred_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

describe("useUpdateTransaction", () => {
  it("успех вызывает PUT и инвалидирует операции и балансы кошельков", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => UPDATED);

    const { result } = renderHook(() => useUpdateTransaction(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "PUT",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/1`,
      body: VALUES,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: transactionsQueryKey(TEST_WORKSPACE_ID),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: walletBalancesQueryKey(TEST_WORKSPACE_ID),
    });
  });

  it("ошибка не вызывает глобальный toast сама по себе (silent)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { amount: ["обязательно"] },
      });
    });

    const { result } = renderHook(() => useUpdateTransaction(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
  });
});

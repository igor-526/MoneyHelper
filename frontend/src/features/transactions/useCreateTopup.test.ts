import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useCreateTopup } from "./useCreateTopup";
import { transactionsQueryKey } from "./useTransactions";
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
  legs: [
    { currency_id: "cur1", amount: "10.00" },
    { currency_id: "cur2", amount: "20.00" },
  ],
};
const CREATED = {
  id: "1",
  wallet_id: "w1",
  category_id: "c1",
  legs: VALUES.legs,
  occurred_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("useCreateTopup", () => {
  it("успех вызывает POST /api/transactions/topups и инвалидирует операции и балансы, legs — в переданном порядке", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => CREATED);

    const { result } = renderHook(() => useCreateTopup(), { wrapper });
    act(() => {
      result.current.mutate(VALUES);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "POST",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/transactions/topups`,
      // `toMatchObject` уже проверяет `legs` в переданном порядке как часть `VALUES`.
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
        detail: "Набор валют пополнения не совпадает с набором валют кошелька",
      });
    });

    const { result } = renderHook(() => useCreateTopup(), { wrapper });
    act(() => {
      result.current.mutate(VALUES);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
  });
});

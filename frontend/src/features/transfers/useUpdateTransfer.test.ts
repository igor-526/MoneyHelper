import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useUpdateTransfer } from "./useUpdateTransfer";
import { TRANSFERS_QUERY_KEY } from "./useTransfers";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, { client: api, children }),
    );
  return { api, toast, invalidateSpy, wrapper };
}

const VALUES = {
  from_wallet_id: "w1",
  to_wallet_id: "w2",
  currency_id: "cur1",
  amount: "20.00",
};
const UPDATED = {
  id: "1",
  ...VALUES,
  occurred_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

describe("useUpdateTransfer", () => {
  it("успех вызывает PUT и инвалидирует переводы и балансы кошельков", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => UPDATED);

    const { result } = renderHook(() => useUpdateTransfer(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "PUT",
      path: "/api/transfers/1",
      body: VALUES,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: TRANSFERS_QUERY_KEY });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["wallet-balances"] });
  });

  it("ошибка не вызывает глобальный toast сама по себе (silent)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { amount: ["обязательно"] },
      });
    });

    const { result } = renderHook(() => useUpdateTransfer(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
  });
});

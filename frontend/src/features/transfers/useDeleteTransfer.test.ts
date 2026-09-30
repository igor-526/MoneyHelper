import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useDeleteTransfer } from "./useDeleteTransfer";
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

describe("useDeleteTransfer", () => {
  it("успех вызывает DELETE и инвалидирует переводы и балансы кошельков", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => undefined);

    const { result } = renderHook(() => useDeleteTransfer(), { wrapper });
    act(() => {
      result.current.mutate("1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({ method: "DELETE", path: "/api/transfers/1" });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: TRANSFERS_QUERY_KEY });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["wallet-balances"] });
  });

  it("ошибка не обрабатывается локально — показывается общим глобальным обработчиком", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "server", status: 500 });
    });

    const { result } = renderHook(() => useDeleteTransfer(), { wrapper });
    act(() => {
      result.current.mutate("1");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledWith("Ошибка сервера, попробуйте позже");
  });
});

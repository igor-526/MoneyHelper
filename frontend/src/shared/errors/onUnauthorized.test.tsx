import { QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { parseApiError } from "@/shared/api";
import { createToastSpy } from "@/test/toastSpy";
import { createQueryClient } from "./createQueryClient";
import type { ErrorMeta } from "./meta";

function setup(onUnauthorized: () => void) {
  const toast = createToastSpy();
  const client = createQueryClient(toast, { onUnauthorized });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { toast, wrapper };
}

describe("onUnauthorized колбэк", () => {
  it("вызывается при unauthorized в запросе", async () => {
    const onUnauthorized = vi.fn();
    const { wrapper } = setup(onUnauthorized);
    const error = parseApiError(401, { detail: "x" });

    const { result } = renderHook(
      () => useQuery({ queryKey: ["q"], queryFn: () => Promise.reject(error), retry: false }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("вызывается при unauthorized в мутации", async () => {
    const onUnauthorized = vi.fn();
    const { wrapper } = setup(onUnauthorized);
    const error = parseApiError(401, { detail: "x" });

    const { result } = renderHook(() => useMutation({ mutationFn: () => Promise.reject(error) }), {
      wrapper,
    });
    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("не вызывается для других видов ошибок", async () => {
    const onUnauthorized = vi.fn();
    const { wrapper } = setup(onUnauthorized);
    const error = parseApiError(500, {});

    const { result } = renderHook(
      () => useQuery({ queryKey: ["q"], queryFn: () => Promise.reject(error), retry: false }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("не вызывается для silent-запроса (первичная проверка сессии)", async () => {
    const onUnauthorized = vi.fn();
    const { toast, wrapper } = setup(onUnauthorized);
    const error = parseApiError(401, { detail: "x" });
    const meta: ErrorMeta = { silent: true };

    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ["session"],
          queryFn: () => Promise.reject(error),
          retry: false,
          meta,
        }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(onUnauthorized).not.toHaveBeenCalled();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("работает без колбэка (необязателен)", async () => {
    const toast = createToastSpy();
    const client = createQueryClient(toast);
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const error = parseApiError(401, { detail: "x" });

    const { result } = renderHook(
      () => useQuery({ queryKey: ["q"], queryFn: () => Promise.reject(error), retry: false }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledTimes(1);
  });
});

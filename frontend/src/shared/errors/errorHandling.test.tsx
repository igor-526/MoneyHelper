import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, type ApiErrorKind, parseApiError } from "@/shared/api";
import { createToastSpy } from "@/test/toastSpy";
import { createQueryClient } from "./createQueryClient";
import type { ErrorMeta } from "./meta";

interface Case {
  name: string;
  error: ApiError;
  text: string;
}

const CASES: Case[] = [
  {
    name: "400 без полей",
    error: parseApiError(400, { detail: "Неверные данные" }),
    text: "Неверные данные",
  },
  {
    name: "400 с полями",
    error: parseApiError(400, {
      detail: [{ loc: ["body", "email"], msg: "неверный email", type: "value_error" }],
    }),
    text: "Проверьте заполнение формы: email: неверный email",
  },
  {
    name: "401",
    error: parseApiError(401, { detail: "x" }),
    text: "Сессия истекла, войдите снова",
  },
  {
    name: "403",
    error: parseApiError(403, { detail: "x" }),
    text: "Недостаточно прав для этого действия",
  },
  { name: "404 без detail", error: parseApiError(404, {}), text: "Не найдено" },
  {
    name: "404 с detail",
    error: parseApiError(404, { detail: "Кошелёк не найден" }),
    text: "Кошелёк не найден",
  },
  {
    name: "409",
    error: parseApiError(409, { detail: "Кошелёк уже существует" }),
    text: "Кошелёк уже существует",
  },
  { name: "500", error: parseApiError(500, undefined), text: "Ошибка сервера, попробуйте позже" },
  {
    name: "сеть",
    error: new ApiError({ kind: "network", status: null }),
    text: "Нет соединения с сервером",
  },
  {
    name: "таймаут",
    error: new ApiError({ kind: "timeout", status: null }),
    text: "Сервер не отвечает, попробуйте позже",
  },
  { name: "прочий статус", error: parseApiError(418, {}), text: "Что-то пошло не так" },
];

function setup() {
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { toast, wrapper };
}

function useFailingQuery(error: unknown, meta?: ErrorMeta) {
  return useQuery({
    queryKey: ["failing"],
    queryFn: () => Promise.reject(error),
    retry: false,
    meta,
  });
}

function useFailingMutation(error: unknown, meta?: ErrorMeta) {
  return useMutation({ mutationFn: () => Promise.reject(error), meta });
}

describe("глобальная обработка ошибок запросов", () => {
  it.each(CASES)("$name: toast показан, запрос не «висит»", async ({ error, text }) => {
    const { toast, wrapper } = setup();
    const { result } = renderHook(() => useFailingQuery(error), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isPending).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith(text);
  });
});

describe("глобальная обработка ошибок мутаций", () => {
  it.each(CASES)("$name: toast показан, мутация не «висит»", async ({ error, text }) => {
    const { toast, wrapper } = setup();
    const { result } = renderHook(() => useFailingMutation(error), { wrapper });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isPending).toBe(false);
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith(text);
  });

  it("ошибка, не связанная с API, тоже не теряется", async () => {
    const { toast, wrapper } = setup();
    const { result } = renderHook(() => useFailingMutation(new TypeError("bug")), { wrapper });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledWith("Что-то пошло не так");
  });
});

describe("переопределение сообщения", () => {
  const conflict = parseApiError(409, { detail: "по умолчанию" });

  it("свой текст для вида ошибки", async () => {
    const { toast, wrapper } = setup();
    const meta: ErrorMeta = { errorMessages: { conflict: "Такой кошелёк уже есть" } };
    const { result } = renderHook(() => useFailingMutation(conflict, meta), { wrapper });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledWith("Такой кошелёк уже есть");
  });

  it("свой текст для других видов не влияет на остальные", async () => {
    const { toast, wrapper } = setup();
    const meta: ErrorMeta = { errorMessages: { conflict: "Такой кошелёк уже есть" } };
    const { result } = renderHook(() => useFailingMutation(parseApiError(500, {}), meta), {
      wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledWith("Ошибка сервера, попробуйте позже");
  });

  it("общий текст для любой ошибки", async () => {
    const { toast, wrapper } = setup();
    const { result } = renderHook(
      () => useFailingMutation(parseApiError(500, {}), { errorMessages: "Не удалось сохранить" }),
      { wrapper },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledWith("Не удалось сохранить");
  });

  it("silent отключает глобальный toast, ошибка доступна вызывающему коду", async () => {
    const { toast, wrapper } = setup();
    const { result } = renderHook(() => useFailingMutation(conflict, { silent: true }), {
      wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
    expect(result.current.error).toBe(conflict);
  });
});

describe("повторы запросов", () => {
  it.each<[ApiErrorKind, boolean]>([
    ["network", true],
    ["server", true],
    ["timeout", true],
    ["validation", false],
    ["forbidden", false],
    ["not_found", false],
    ["conflict", false],
    ["unauthorized", false],
  ])("вид %s повторяется: %s", async (kind, retried) => {
    const { shouldRetryQuery } = await import("./createQueryClient");
    expect(shouldRetryQuery(0, new ApiError({ kind, status: null }))).toBe(retried);
    expect(shouldRetryQuery(1, new ApiError({ kind, status: null }))).toBe(false);
  });
});

import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useBucketLabelResolvers } from "./useBucketLabelResolvers";

const TEST_WORKSPACE_ID = "workspace-1";

function page(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

const WALLETS = [
  {
    id: "w1",
    name: "Наличные",
    icon: "wallet",
    currency_id: "cur1",
    created_at: "",
    updated_at: null,
  },
];
const CATEGORIES = [
  { id: "c1", type: "income", name: "Зарплата", icon: "wallet", created_at: "", updated_at: null },
];
const CURRENCIES = [{ id: "cur1", code: "USD", name: "Доллар США", decimal_places: 2 }];

function handler(request: Parameters<FakeHandler>[0]) {
  if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`) return page(WALLETS);
  if (request.path === `/api/workspaces/${TEST_WORKSPACE_ID}/categories`) return page(CATEGORIES);
  if (request.path === "/api/currencies") return page(CURRENCIES);
  throw new Error(`unexpected request: ${request.path}`);
}

function setup() {
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
  return { wrapper };
}

describe("useBucketLabelResolvers", () => {
  it("резолвер wallet возвращает название кошелька по id, undefined для неизвестного", async () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useBucketLabelResolvers(), { wrapper });

    await waitFor(() => expect(result.current.wallet("w1")).toBe("Наличные"));
    expect(result.current.wallet("unknown")).toBeUndefined();
  });

  it("резолвер category возвращает название категории по id, undefined для неизвестного", async () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useBucketLabelResolvers(), { wrapper });

    await waitFor(() => expect(result.current.category("c1")).toBe("Зарплата"));
    expect(result.current.category("unknown")).toBeUndefined();
  });

  it("резолвер currency возвращает код валюты по id, undefined для неизвестного", async () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useBucketLabelResolvers(), { wrapper });

    await waitFor(() => expect(result.current.currency("cur1")).toBe("USD"));
    expect(result.current.currency("unknown")).toBeUndefined();
  });
});

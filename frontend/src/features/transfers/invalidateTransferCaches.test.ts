import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { invalidateTransferCaches } from "./invalidateTransferCaches";

describe("invalidateTransferCaches", () => {
  it("инвалидирует списки переводов и балансы кошельков воркспейса", () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");

    invalidateTransferCaches(client, "ws1");

    expect(spy.mock.calls.map(([filters]) => filters?.queryKey)).toEqual([
      ["transfers", "ws1"],
      ["wallet-balances", "ws1"],
    ]);
  });
});

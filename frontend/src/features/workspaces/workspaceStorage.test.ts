import { afterEach, describe, expect, it, vi } from "vitest";
import { workspaceStorage } from "./workspaceStorage";

afterEach(() => vi.restoreAllMocks());

describe("workspaceStorage", () => {
  it("сохраняет и восстанавливает выбранный воркспейс", () => {
    workspaceStorage.set("workspace-1");
    expect(window.localStorage.getItem("moneyhelper.workspace")).toBe("workspace-1");
    expect(workspaceStorage.get()).toBe("workspace-1");
  });

  it("возвращает null, если ничего не сохранено", () => {
    expect(workspaceStorage.get()).toBeNull();
  });

  it("не падает, если хранилище недоступно", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    expect(workspaceStorage.get()).toBeNull();
    expect(() => workspaceStorage.set("workspace-1")).not.toThrow();
  });
});

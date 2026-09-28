import { afterEach, describe, expect, it, vi } from "vitest";
import { localThemeStorage } from "./storage";

afterEach(() => vi.restoreAllMocks());

describe("localThemeStorage", () => {
  it("сохраняет и восстанавливает режим", () => {
    localThemeStorage.set("dark");
    expect(window.localStorage.getItem("moneyhelper.theme")).toBe("dark");
    expect(localThemeStorage.get()).toBe("dark");
  });

  it("игнорирует некорректное значение", () => {
    window.localStorage.setItem("moneyhelper.theme", "blue");
    expect(localThemeStorage.get()).toBe("system");
  });

  it("не падает, если хранилище недоступно", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    expect(localThemeStorage.get()).toBe("system");
    expect(() => localThemeStorage.set("dark")).not.toThrow();
  });
});

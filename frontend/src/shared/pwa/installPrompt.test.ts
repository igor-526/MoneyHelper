import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { setMedia } from "@/test/matchMedia";
import {
  createInstallPromptStore,
  detectIos,
  detectStandalone,
  useInstallPrompt,
} from "./installPrompt";

function installEvent(outcome: "accepted" | "dismissed" = "accepted") {
  const event = new Event("beforeinstallprompt", { cancelable: true }) as Event & {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: string }>;
  };
  event.prompt = vi.fn(async () => undefined);
  event.userChoice = Promise.resolve({ outcome });
  return event;
}

describe("createInstallPromptStore", () => {
  it("перехватывает beforeinstallprompt и разрешает установку", () => {
    const target = new EventTarget();
    const store = createInstallPromptStore(target);
    expect(store.getSnapshot()).toBe(false);

    const event = installEvent();
    target.dispatchEvent(event);

    expect(store.getSnapshot()).toBe(true);
    expect(event.defaultPrevented).toBe(true);
  });

  it("prompt показывает системный диалог и сообщает результат", async () => {
    const target = new EventTarget();
    const store = createInstallPromptStore(target);
    const event = installEvent("accepted");
    target.dispatchEvent(event);

    await expect(store.prompt()).resolves.toBe(true);
    expect(event.prompt).toHaveBeenCalledTimes(1);
    expect(store.getSnapshot()).toBe(false);
  });

  it("отказ пользователя возвращает false", async () => {
    const target = new EventTarget();
    const store = createInstallPromptStore(target);
    target.dispatchEvent(installEvent("dismissed"));
    await expect(store.prompt()).resolves.toBe(false);
  });

  it("после установки (appinstalled) кнопка скрывается", () => {
    const target = new EventTarget();
    const store = createInstallPromptStore(target);
    target.dispatchEvent(installEvent());
    target.dispatchEvent(new Event("appinstalled"));
    expect(store.getSnapshot()).toBe(false);
  });

  it("без события prompt ничего не делает", async () => {
    const store = createInstallPromptStore(new EventTarget());
    await expect(store.prompt()).resolves.toBe(false);
  });
});

describe("useInstallPrompt", () => {
  it("отражает доступность установки", () => {
    const target = new EventTarget();
    const store = createInstallPromptStore(target);
    const { result } = renderHook(() => useInstallPrompt(store));
    expect(result.current.canInstall).toBe(false);

    act(() => void target.dispatchEvent(installEvent()));
    expect(result.current.canInstall).toBe(true);
  });

  it("определяет режим standalone", () => {
    setMedia("(display-mode: standalone)", true);
    const store = createInstallPromptStore(new EventTarget());
    const { result } = renderHook(() => useInstallPrompt(store));
    expect(result.current.isStandalone).toBe(true);
  });
});

describe("detectIos / detectStandalone", () => {
  it.each([
    ["Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", 5, true],
    ["Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)", 5, true],
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", 5, true],
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", 0, false],
    ["Mozilla/5.0 (Linux; Android 14; Pixel 8)", 5, false],
  ])("%s (touch=%s) -> %s", (userAgent, maxTouchPoints, expected) => {
    expect(detectIos({ userAgent, maxTouchPoints })).toBe(expected);
  });

  it("navigator.standalone тоже считается установленным приложением", () => {
    const win = { matchMedia: () => ({ matches: false }), navigator: { standalone: true } };
    expect(detectStandalone(win as unknown as Window & { navigator: Navigator })).toBe(true);
  });
});

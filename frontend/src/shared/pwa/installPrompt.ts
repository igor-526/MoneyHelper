import { useCallback, useSyncExternalStore } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export interface InstallPromptStore {
  subscribe(listener: () => void): () => void;
  /** Доступна ли установка (получено `beforeinstallprompt`, приложение ещё не установлено). */
  getSnapshot(): boolean;
  /** Показывает системный диалог установки; `true`, если пользователь согласился. */
  prompt(): Promise<boolean>;
}

/**
 * Перехватывает `beforeinstallprompt`. Store создаётся при старте приложения, потому что событие
 * приходит один раз и раньше, чем откроется страница с кнопкой установки.
 */
export function createInstallPromptStore(target: EventTarget = window): InstallPromptStore {
  let deferred: BeforeInstallPromptEvent | null = null;
  const listeners = new Set<() => void>();
  const emit = () => listeners.forEach((listener) => listener());

  target.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferred = event as BeforeInstallPromptEvent;
    emit();
  });
  target.addEventListener("appinstalled", () => {
    deferred = null;
    emit();
  });

  return {
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getSnapshot: () => deferred !== null,
    async prompt() {
      const event = deferred;
      if (!event) return false;
      await event.prompt();
      const { outcome } = await event.userChoice;
      deferred = null;
      emit();
      return outcome === "accepted";
    },
  };
}

let defaultStore: InstallPromptStore | null = null;

/** Запускает перехват события установки; вызывается один раз при старте приложения. */
export function startInstallPromptCapture(): InstallPromptStore {
  defaultStore ??= createInstallPromptStore();
  return defaultStore;
}

export function detectIos(nav: Pick<Navigator, "userAgent" | "maxTouchPoints">): boolean {
  if (/iphone|ipad|ipod/i.test(nav.userAgent)) return true;
  // iPadOS 13+ выдаёт себя за Mac, но имеет мультитач
  return /macintosh/i.test(nav.userAgent) && nav.maxTouchPoints > 1;
}

export function detectStandalone(
  win: Window & { navigator: Navigator & { standalone?: boolean } },
): boolean {
  return (
    (typeof win.matchMedia === "function" &&
      win.matchMedia("(display-mode: standalone)").matches) ||
    win.navigator.standalone === true
  );
}

export interface InstallPrompt {
  canInstall: boolean;
  install: () => Promise<boolean>;
  isStandalone: boolean;
  isIos: boolean;
}

const NOOP_STORE: InstallPromptStore = {
  subscribe: () => () => undefined,
  getSnapshot: () => false,
  prompt: async () => false,
};

export function useInstallPrompt(
  store: InstallPromptStore = defaultStore ?? NOOP_STORE,
): InstallPrompt {
  const canInstall = useSyncExternalStore(store.subscribe, store.getSnapshot, () => false);
  const install = useCallback(() => store.prompt(), [store]);
  return {
    canInstall,
    install,
    isStandalone: detectStandalone(window),
    isIos: detectIos(navigator),
  };
}

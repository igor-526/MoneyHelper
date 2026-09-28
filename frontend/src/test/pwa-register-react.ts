import { useSyncExternalStore } from "react";
import { vi } from "vitest";

/** Управляемая подмена `virtual:pwa-register/react` для тестов (алиас в vitest.config.ts). */
interface State {
  needRefresh: boolean;
  offlineReady: boolean;
}

let state: State = { needRefresh: false, offlineReady: false };
const listeners = new Set<() => void>();

export const updateServiceWorker = vi.fn<(reload?: boolean) => Promise<void>>(
  async () => undefined,
);

export const pwaMock = {
  set(next: Partial<State>) {
    state = { ...state, ...next };
    listeners.forEach((listener) => listener());
  },
  reset() {
    state = { needRefresh: false, offlineReady: false };
    updateServiceWorker.mockClear();
  },
};

export function useRegisterSW() {
  const current = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => state,
  );
  return {
    needRefresh: [current.needRefresh, () => undefined] as const,
    offlineReady: [current.offlineReady, () => undefined] as const,
    updateServiceWorker,
  };
}

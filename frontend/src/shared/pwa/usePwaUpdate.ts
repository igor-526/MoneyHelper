import { useRegisterSW } from "virtual:pwa-register/react";

export interface PwaUpdate {
  /** Доступна новая версия приложения. */
  needRefresh: boolean;
  /** Активирует новую версию и перезагружает страницу. */
  update: () => Promise<void>;
}

/** Обёртка над регистрацией service worker; новая версия применяется только по подтверждению пользователя. */
export function usePwaUpdate(): PwaUpdate {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW();
  return { needRefresh, update: () => updateServiceWorker(true) };
}

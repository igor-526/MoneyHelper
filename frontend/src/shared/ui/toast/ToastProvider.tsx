import { App as AntApp } from "antd";
import type { ArgsProps } from "antd/es/message";
import { createContext, type ReactNode, useContext, useMemo, useRef } from "react";
import type { ToastApi } from "./types";

export const ERROR_DURATION_S = 8;
export const DEFAULT_DURATION_S = 4;
export const MAX_TOASTS = 3;

type ToastType = "error" | "success" | "warning";

const ToastContext = createContext<ToastApi | null>(null);

function ToastBridge({ children }: { children: ReactNode }) {
  const { message } = AntApp.useApp();
  // Признак чередования длительности для активных уведомлений (см. ниже)
  const parity = useRef(new Map<string, boolean>());

  const api = useMemo<ToastApi>(() => {
    const show = (type: ToastType, text: string) => {
      // Одинаковые тип и текст обновляют то же уведомление (дедупликация). antd перезапускает таймер
      // только при смене длительности, поэтому при повторе она чередуется на 1 мс.
      const key = `${type}:${text}`;
      const odd = !(parity.current.get(key) ?? true);
      parity.current.set(key, odd);
      const base = type === "error" ? ERROR_DURATION_S : DEFAULT_DURATION_S;
      // `role` не описан в типах antd, но передаётся до rc-notification (покрыто тестом); по умолчанию там alert
      const config: ArgsProps & { role: "alert" | "status" } = {
        key,
        type,
        duration: odd ? base + 0.001 : base,
        role: type === "error" ? "alert" : "status",
        content: <span style={{ cursor: "pointer" }}>{text}</span>,
        onClick: () => message.destroy(key),
        onClose: () => parity.current.delete(key),
      };
      message.open(config);
      return key;
    };
    return {
      error: (text) => show("error", text),
      success: (text) => show("success", text),
      warning: (text) => show("warning", text),
      dismiss: (id) => message.destroy(id),
    };
  }, [message]);

  return <ToastContext.Provider value={api}>{children}</ToastContext.Provider>;
}

/** Содержит antd `App` (контекст для `message`); уведомления сверху с учётом безопасной зоны экрана. */
export function ToastProvider({ children }: { children: ReactNode }) {
  return (
    <AntApp
      message={{ maxCount: MAX_TOASTS, top: "calc(env(safe-area-inset-top, 0px) + 8px)" }}
      component={false}
    >
      <ToastBridge>{children}</ToastBridge>
    </AntApp>
  );
}

export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) {
    throw new Error("useToast нужно вызывать внутри ToastProvider");
  }
  return api;
}

export type ToastId = string;

/** Интерфейс уведомлений: компоненты и hooks зависят от него, а не от antd `message`. */
export interface ToastApi {
  error(text: string): ToastId;
  success(text: string): ToastId;
  warning(text: string): ToastId;
  dismiss(id: ToastId): void;
}

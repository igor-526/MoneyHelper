import { vi } from "vitest";
import type { ToastApi } from "@/shared/ui/toast/types";

export type ToastSpy = { [K in keyof ToastApi]: ReturnType<typeof vi.fn> } & ToastApi;

export function createToastSpy(): ToastSpy {
  return {
    error: vi.fn((text: string) => `error:${text}`),
    success: vi.fn((text: string) => `success:${text}`),
    warning: vi.fn((text: string) => `warning:${text}`),
    dismiss: vi.fn(),
  } as unknown as ToastSpy;
}

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setMedia } from "@/test/matchMedia";
import { ToastProvider } from "@/shared/ui";

const state = vi.hoisted(() => ({
  value: { canInstall: false, install: async () => true, isStandalone: false, isIos: false },
}));

vi.mock("@/shared/pwa/installPrompt", () => ({
  useInstallPrompt: () => state.value,
}));

import { InstallSection } from "./InstallSection";

function renderSection(overrides: Partial<typeof state.value>) {
  state.value = {
    canInstall: false,
    install: async () => true,
    isStandalone: false,
    isIos: false,
    ...overrides,
  };
  return render(
    <ToastProvider>
      <InstallSection />
    </ToastProvider>,
  );
}

afterEach(() => setMedia("(display-mode: standalone)", false));

describe("InstallSection", () => {
  it("показывает кнопку установки, когда установка доступна", async () => {
    const install = vi.fn(async () => true);
    renderSection({ canInstall: true, install });
    await userEvent.click(screen.getByRole("button", { name: /Установить приложение/ }));
    expect(install).toHaveBeenCalledTimes(1);
  });

  it("на iOS показывает инструкцию", () => {
    renderSection({ isIos: true });
    expect(screen.getByText(/На экран Домой/)).toBeInTheDocument();
  });

  it("в режиме standalone ничего не показывает", () => {
    const { container } = renderSection({ isStandalone: true, canInstall: true, isIos: true });
    expect(container).toBeEmptyDOMElement();
  });

  it("ошибка установки не остаётся молчаливой: показывается toast", async () => {
    renderSection({ canInstall: true, install: async () => Promise.reject(new Error("fail")) });
    await userEvent.click(screen.getByRole("button", { name: /Установить приложение/ }));
    expect(await screen.findByText("Не удалось открыть установку приложения")).toBeInTheDocument();
  });

  it("вне iOS и без события установки блок пуст", () => {
    const { container } = renderSection({});
    expect(container).toBeEmptyDOMElement();
  });
});

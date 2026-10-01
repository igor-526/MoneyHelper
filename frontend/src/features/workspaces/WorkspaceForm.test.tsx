import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { setMedia } from "@/test/matchMedia";
import type { Workspace } from "./Workspace";
import { WorkspaceForm } from "./WorkspaceForm";

const WORKSPACE: Workspace = {
  id: "5",
  name: "Личное",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

/** Настоящий `ToastProvider`, чтобы проверять видимые уведомления, как использует их компонент. */
function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("WorkspaceForm", () => {
  it("создание: успех добавляет воркспейс, вызывает onSuccess и закрывает форму", async () => {
    const CREATED = {
      id: "9",
      name: "Поездка",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    render(<WorkspaceForm open onClose={onClose} onSuccess={onSuccess} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Поездка");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "POST",
      path: "/api/workspaces",
      body: { name: "Поездка" },
    });
    expect(onSuccess).toHaveBeenCalledWith(CREATED);
    expect(await screen.findByText("Воркспейс создан")).toBeInTheDocument();
  });

  it("переименование: поле предзаполнено, успех обновляет воркспейс", async () => {
    const UPDATED = { ...WORKSPACE, name: "Обновлённый" };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<WorkspaceForm open workspace={WORKSPACE} onClose={onClose} />, { wrapper });

    expect(screen.getByLabelText("Название")).toHaveValue("Личное");

    await userEvent.clear(screen.getByLabelText("Название"));
    await userEvent.type(screen.getByLabelText("Название"), "Обновлённый");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: "/api/workspaces/5",
      body: { name: "Обновлённый" },
    });
    expect(await screen.findByText("Воркспейс переименован")).toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["Название не может быть пустым"] },
      });
    });
    const onClose = vi.fn();
    render(<WorkspaceForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "  ");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Название не может быть пустым")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => WORKSPACE);
    render(<WorkspaceForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => WORKSPACE);
    render(<WorkspaceForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});

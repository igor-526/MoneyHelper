import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { setMedia } from "@/test/matchMedia";
import type { Category } from "./Category";
import { CategoryForm } from "./CategoryForm";

const TEST_WORKSPACE_ID = "workspace-1";

const CATEGORY: Category = {
  id: "5",
  type: "income",
  name: "Зарплата",
  icon: "banknote",
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
        <WorkspaceContext.Provider value={TEST_WORKSPACE_ID}>
          <ToastProvider>{children}</ToastProvider>
        </WorkspaceContext.Provider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

async function selectIcon(name: string) {
  await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));
  await userEvent.click(await screen.findByRole("option", { name }));
}

/** Радио-инпут `Segmented` скрыт (`pointer-events: none`), клик идёт по видимой подписи. */
async function selectType(label: "Доход" | "Расход") {
  await userEvent.click(screen.getByText(label));
}

describe("CategoryForm", () => {
  it("создание категории дохода: успех добавляет категорию и закрывает форму", async () => {
    const CREATED = {
      id: "9",
      type: "income",
      name: "Подработка",
      icon: "banknote",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<CategoryForm open onClose={onClose} />, { wrapper });

    await selectType("Доход");
    await userEvent.type(screen.getByLabelText("Название"), "Подработка");
    await selectIcon("banknote");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "POST",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/categories`,
      body: { type: "income", name: "Подработка", icon: "banknote" },
    });
    expect(await screen.findByText("Категория создана")).toBeInTheDocument();
  });

  it("создание категории расхода: успех добавляет категорию и закрывает форму", async () => {
    const CREATED = {
      id: "10",
      type: "expense",
      name: "Транспорт",
      icon: "coins",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    };
    const { api, wrapper } = setup(() => CREATED);
    const onClose = vi.fn();
    render(<CategoryForm open onClose={onClose} />, { wrapper });

    await selectType("Расход");
    await userEvent.type(screen.getByLabelText("Название"), "Транспорт");
    await selectIcon("coins");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "POST",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/categories`,
      body: { type: "expense", name: "Транспорт", icon: "coins" },
    });
    expect(await screen.findByText("Категория создана")).toBeInTheDocument();
  });

  it("предзаполняет type из defaultType при создании", async () => {
    const { wrapper } = setup(() => CATEGORY);
    render(<CategoryForm open onClose={vi.fn()} defaultType="expense" />, { wrapper });

    expect(screen.getByRole("radio", { name: "Расход" })).toBeChecked();
  });

  it("редактирование: поля предзаполнены, успех обновляет категорию", async () => {
    const UPDATED = { ...CATEGORY, name: "Обновлённая" };
    const { api, wrapper } = setup(() => UPDATED);
    const onClose = vi.fn();
    render(<CategoryForm open category={CATEGORY} onClose={onClose} />, { wrapper });

    expect(screen.getByRole("radio", { name: "Доход" })).toBeChecked();
    expect(screen.getByLabelText("Название")).toHaveValue("Зарплата");
    expect(document.querySelector('[data-icon="banknote"]')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Название"));
    await userEvent.type(screen.getByLabelText("Название"), "Обновлённая");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.requests.at(-1)).toMatchObject({
      method: "PUT",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/categories/5`,
      body: { type: "income", name: "Обновлённая", icon: "banknote" },
    });
    expect(await screen.findByText("Категория обновлена")).toBeInTheDocument();
  });

  it("ошибка валидации по полю остаётся в форме и не закрывает её", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["Название слишком длинное"] },
      });
    });
    const onClose = vi.fn();
    render(<CategoryForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Дубликат");
    await selectIcon("banknote");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(await screen.findByText("Название слишком длинное")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("конфликт имени (409) показывает сообщение на поле name, не закрывает форму и не вызывает toast", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "conflict", status: 409, detail: "Дубликат" });
    });
    const onClose = vi.fn();
    render(<CategoryForm open onClose={onClose} />, { wrapper });

    await userEvent.type(screen.getByLabelText("Название"), "Зарплата");
    await selectIcon("banknote");
    await userEvent.click(screen.getByRole("button", { name: "Создать" }));

    expect(
      await screen.findByText("Категория с таким названием уже существует в этом типе"),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.queryByText("Дубликат")).not.toBeInTheDocument();
  });

  it("на телефоне открывается в Drawer", () => {
    const { wrapper } = setup(() => CATEGORY);
    render(<CategoryForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", () => {
    setMedia(DESKTOP_QUERY, true);
    const { wrapper } = setup(() => CATEGORY);
    render(<CategoryForm open onClose={vi.fn()} />, { wrapper });

    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });
});

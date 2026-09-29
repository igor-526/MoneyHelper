import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { ToastProvider } from "@/shared/ui";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { CategoriesPage } from "./CategoriesPage";

function categoriesPage(items: unknown[]) {
  return { items, total: items.length, limit: 100, offset: 0 };
}

const CATEGORIES = [
  {
    id: "1",
    type: "income",
    name: "Зарплата",
    icon: "banknote",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: "2",
    type: "expense",
    name: "Продукты",
    icon: "coins",
    created_at: "2026-01-02T00:00:00Z",
    updated_at: null,
  },
];

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>
        <ToastProvider>{children}</ToastProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, toast, wrapper };
}

describe("CategoriesPage", () => {
  it("загрузка и рендер списка карточек с индикаторами типа", async () => {
    const { wrapper } = setup(() => categoriesPage(CATEGORIES));
    render(<CategoriesPage />, { wrapper });

    expect(await screen.findByText("Зарплата")).toBeInTheDocument();
    expect(screen.getByText("Продукты")).toBeInTheDocument();
    const tags = document.querySelectorAll(".ant-tag");
    expect(Array.from(tags).map((tag) => tag.textContent)).toEqual(["Доход", "Расход"]);
  });

  it("переключение фильтра меняет отображаемый набор и повторно запрашивает список с нужным type", async () => {
    const { api, wrapper } = setup((request) => {
      if (request.query?.type === "income") return categoriesPage([CATEGORIES[0]]);
      return categoriesPage(CATEGORIES);
    });
    render(<CategoriesPage />, { wrapper });
    await screen.findByText("Зарплата");
    expect(screen.getByText("Продукты")).toBeInTheDocument();

    // Радио-инпут `Segmented` скрыт (`pointer-events: none`), клик идёт по видимой подписи;
    // текст «Доход» неоднозначен (есть ещё в теге карточки), поэтому область сужена до фильтра.
    const filterGroup = screen.getByRole("radiogroup", { name: "Фильтр по типу" });
    await userEvent.click(within(filterGroup).getByText("Доход"));

    await waitFor(() => expect(screen.queryByText("Продукты")).not.toBeInTheDocument());
    expect(screen.getByText("Зарплата")).toBeInTheDocument();
    expect(
      api.requests.some(
        (r) => r.path === "/api/categories" && (r.query as { type?: string })?.type === "income",
      ),
    ).toBe(true);
  });

  it("пустой отфильтрованный список показывает EmptyState, фильтр остаётся видимым", async () => {
    const { wrapper } = setup(() => categoriesPage([]));
    render(<CategoriesPage />, { wrapper });

    expect(await screen.findByText("Категорий пока нет")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Все" })).toBeInTheDocument();
  });

  it("кнопка действия открывает форму создания с предзаполненным defaultType", async () => {
    const { wrapper } = setup(() => categoriesPage([]));
    render(<CategoriesPage />, { wrapper });
    await screen.findByText("Категорий пока нет");

    // Радио-инпут `Segmented` скрыт (`pointer-events: none`), клик идёт по видимой подписи.
    await userEvent.click(screen.getByText("Расход"));
    await waitFor(() => expect(screen.getByRole("radio", { name: "Расход" })).toBeChecked());

    await userEvent.click(screen.getByRole("button", { name: "Создать категорию" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText("Название")).toHaveValue("");
    expect(within(dialog).getByRole("radio", { name: "Расход" })).toBeChecked();
  });

  it("кнопка «Редактировать» карточки открывает форму с ожидаемыми пропами", async () => {
    const { wrapper } = setup(() => categoriesPage(CATEGORIES));
    render(<CategoriesPage />, { wrapper });
    await screen.findByText("Зарплата");

    const [editButton] = screen.getAllByRole("button", { name: "Редактировать" });
    await userEvent.click(editButton as HTMLElement);

    expect(await screen.findByLabelText("Название")).toHaveValue("Зарплата");
  });

  it("ошибка загрузки показывает toast (общий обработчик)", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });
    render(<CategoriesPage />, { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });
});

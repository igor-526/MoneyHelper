import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { Category } from "./Category";
import { CategoryCard } from "./CategoryCard";

const INCOME: Category = {
  id: "5",
  type: "income",
  name: "Зарплата",
  icon: "banknote",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const EXPENSE: Category = {
  id: "6",
  type: "expense",
  name: "Продукты",
  icon: "coins",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <ApiClientProvider client={api}>{children}</ApiClientProvider>
    </QueryClientProvider>
  );
  return { api, wrapper };
}

describe("CategoryCard", () => {
  it("отображает иконку, название и индикатор типа «Доход»", () => {
    const { wrapper } = setup(() => undefined);
    render(<CategoryCard category={INCOME} onEdit={vi.fn()} />, { wrapper });

    expect(document.querySelector('[data-icon="banknote"]')).toBeInTheDocument();
    expect(screen.getByText("Зарплата")).toBeInTheDocument();
    expect(screen.getByText("Доход")).toBeInTheDocument();
  });

  it("отображает иконку, название и индикатор типа «Расход»", () => {
    const { wrapper } = setup(() => undefined);
    render(<CategoryCard category={EXPENSE} onEdit={vi.fn()} />, { wrapper });

    expect(document.querySelector('[data-icon="coins"]')).toBeInTheDocument();
    expect(screen.getByText("Продукты")).toBeInTheDocument();
    expect(screen.getByText("Расход")).toBeInTheDocument();
  });

  it("нажатие «Редактировать» вызывает onEdit с этой категорией", async () => {
    const { wrapper } = setup(() => undefined);
    const onEdit = vi.fn();
    render(<CategoryCard category={INCOME} onEdit={onEdit} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Редактировать" }));

    expect(onEdit).toHaveBeenCalledWith(INCOME);
  });

  it("подтверждение в Popconfirm вызывает DELETE /api/categories/{id}", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(<CategoryCard category={INCOME} onEdit={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    await waitFor(() =>
      expect(
        api.requests.some((r) => r.method === "DELETE" && r.path === "/api/categories/5"),
      ).toBe(true),
    );
  });

  it("отмена подтверждения не вызывает запрос", async () => {
    const { api, wrapper } = setup(() => undefined);
    render(<CategoryCard category={INCOME} onEdit={vi.fn()} />, { wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(api.requests).toHaveLength(0);
  });
});

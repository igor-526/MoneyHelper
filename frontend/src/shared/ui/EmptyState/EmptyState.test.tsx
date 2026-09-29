import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("минимальный рендер: только иконка и заголовок", () => {
    const { container } = render(<EmptyState icon="wallet" title="Пока нет кошельков" />);

    expect(container.querySelector('[data-icon="wallet"]')).toBeInTheDocument();
    expect(screen.getByText("Пока нет кошельков")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("рендерит описание под заголовком", () => {
    render(
      <EmptyState icon="wallet" title="Пока нет кошельков" description="Добавьте первый кошелёк" />,
    );

    expect(screen.getByText("Добавьте первый кошелёк")).toBeInTheDocument();
  });

  it("рендерит кнопку действия и вызывает onClick", async () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        icon="wallet"
        title="Пока нет кошельков"
        action={{ label: "Добавить кошелёк", onClick }}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Добавить кошелёк" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("без action кнопка не отображается", () => {
    render(<EmptyState icon="wallet" title="Пока нет кошельков" />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function Broken(): never {
  throw new Error("сбой рендеринга");
}

describe("ErrorBoundary", () => {
  it("показывает экран ошибки с кнопкой «Перезагрузить»", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const onReload = vi.fn();
    render(
      <ErrorBoundary onReload={onReload}>
        <Broken />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Что-то пошло не так");
    await userEvent.click(screen.getByRole("button", { name: "Перезагрузить" }));
    expect(onReload).toHaveBeenCalledTimes(1);
    spy.mockRestore();
  });

  it("не мешает нормальному рендерингу", () => {
    render(
      <ErrorBoundary>
        <p>содержимое</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("содержимое")).toBeInTheDocument();
  });
});

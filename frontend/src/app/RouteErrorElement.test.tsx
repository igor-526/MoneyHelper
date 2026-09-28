import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { RouteErrorElement } from "./RouteErrorElement";

function Broken(): never {
  throw new Error("сбой в маршруте");
}

describe("RouteErrorElement", () => {
  it("ошибка рендеринга страницы показывает экран ошибки", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const router = createMemoryRouter([
      { path: "/", element: <Broken />, errorElement: <RouteErrorElement /> },
    ]);
    render(<RouterProvider router={router} />);
    expect(screen.getByRole("button", { name: "Перезагрузить" })).toBeInTheDocument();
    spy.mockRestore();
  });
});

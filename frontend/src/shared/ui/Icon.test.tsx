import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Icon } from "./Icon";
import { FALLBACK_ICON, ICONS, resolveIcon } from "./icons";

describe("Icon", () => {
  it("рендерит известную иконку по имени из БД", () => {
    const { container } = render(<Icon name="wallet" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute("data-icon", "wallet");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("для неизвестного имени показывает запасную иконку без ошибки", () => {
    const { container } = render(<Icon name="no-such-icon" />);
    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(resolveIcon("no-such-icon")).toBe(FALLBACK_ICON);
  });

  it("имя нечувствительно к регистру и пробелам по краям", () => {
    expect(resolveIcon(" Credit-Card ")).toBe(ICONS["credit-card"]);
  });

  it("с подписью иконка доступна скринридеру", () => {
    const { getByRole } = render(<Icon name="wallet" label="Кошелёк" />);
    expect(getByRole("img", { name: "Кошелёк" })).toBeInTheDocument();
  });
});

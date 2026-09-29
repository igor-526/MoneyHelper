import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setMedia } from "@/test/matchMedia";
import { BUSINESS_ICON_NAMES } from "@/shared/ui/icons";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { IconPicker } from "./IconPicker";

describe("IconPicker", () => {
  it("показывает превью выбранной иконки", () => {
    const { container } = render(<IconPicker value="wallet" onChange={vi.fn()} />);

    expect(container.querySelector('[data-icon="wallet"]')).toBeInTheDocument();
  });

  it("сообщает, что иконка не выбрана", () => {
    const { container } = render(<IconPicker value={undefined} onChange={vi.fn()} />);

    expect(screen.getByText("Иконка не выбрана")).toBeInTheDocument();
    expect(container.querySelector("[data-icon]")).not.toBeInTheDocument();
  });

  it("на телефоне открывается в Drawer", async () => {
    setMedia(DESKTOP_QUERY, false);
    render(<IconPicker value={undefined} onChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).not.toBeInTheDocument();
  });

  it("на широком экране открывается в Modal", async () => {
    setMedia(DESKTOP_QUERY, true);
    render(<IconPicker value={undefined} onChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(document.querySelector(".ant-modal")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer")).not.toBeInTheDocument();
  });

  it("выбор иконки вызывает onChange и закрывает контейнер", async () => {
    const onChange = vi.fn();
    render(<IconPicker value={undefined} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));
    await userEvent.click(await screen.findByRole("option", { name: "wallet" }));

    expect(onChange).toHaveBeenCalledWith("wallet");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("список состоит ровно из BUSINESS_ICON_NAMES", async () => {
    render(<IconPicker value={undefined} onChange={vi.fn()} />);

    await userEvent.click(screen.getByRole("button", { name: "Иконка не выбрана" }));

    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.getAttribute("aria-label")).sort()).toEqual(
      [...BUSINESS_ICON_NAMES].sort(),
    );
  });
});

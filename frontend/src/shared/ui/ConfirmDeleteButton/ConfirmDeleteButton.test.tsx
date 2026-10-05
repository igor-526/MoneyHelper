import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDeleteButton } from "./ConfirmDeleteButton";

describe("ConfirmDeleteButton", () => {
  it("подтверждение вызывает onConfirm", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDeleteButton title="Удалить расход?" loading={false} onConfirm={onConfirm} />);

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByText("Удалить расход?")).toBeInTheDocument();
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Удалить" }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("отмена не вызывает onConfirm", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDeleteButton title="Удалить расход?" loading={false} onConfirm={onConfirm} />);

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    const popup = await screen.findByRole("tooltip");
    await userEvent.click(within(popup).getByRole("button", { name: "Отмена" }));

    expect(onConfirm).not.toHaveBeenCalled();
  });
});

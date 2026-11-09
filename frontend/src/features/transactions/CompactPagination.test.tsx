import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CompactPagination, pageWindow } from "./CompactPagination";

describe("pageWindow", () => {
  it.each([
    [1, 100, [1, 2]],
    [50, 100, [49, 50, 51]],
    [100, 100, [99, 100]],
    [1, 1, [1]],
  ])("страница %s из %s", (current, total, expected) => {
    expect(pageWindow(current as number, total as number)).toEqual(expected);
  });
});

it("показывает стрелки только когда крайняя страница не видна среди соседей", async () => {
  const onChange = vi.fn();
  const { rerender } = render(<CompactPagination current={2} total={4} onChange={onChange} />);
  expect(screen.queryByRole("button", { name: "Первая страница" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Последняя страница" }));
  expect(onChange).toHaveBeenCalledWith(4);
  rerender(<CompactPagination current={3} total={4} onChange={onChange} />);
  expect(screen.queryByRole("button", { name: "Последняя страница" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Первая страница" }));
  expect(onChange).toHaveBeenLastCalledWith(1);
  expect(screen.getAllByRole("button")).toHaveLength(4);
});

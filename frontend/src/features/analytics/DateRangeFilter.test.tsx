import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import dayjs from "dayjs";
import { describe, expect, it, vi } from "vitest";
import { DATE_RANGE_PRESETS } from "./dateRangePresets";
import { DateRangeFilter } from "./DateRangeFilter";

describe("DateRangeFilter", () => {
  it("показывает четыре быстрые кнопки в заданном порядке", () => {
    render(<DateRangeFilter value={null} onChange={vi.fn()} />);

    const labels = DATE_RANGE_PRESETS.map((preset) => preset.label);
    for (const label of labels) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("нажатие на кнопку передаёт соответствующий диапазон", async () => {
    const onChange = vi.fn();
    render(<DateRangeFilter value={null} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Месяц" }));

    const [from, to] = onChange.mock.calls[0]![0] as [dayjs.Dayjs, dayjs.Dayjs];
    expect(from.isSame(dayjs().startOf("month"), "day")).toBe(true);
    expect(to.isSame(dayjs().endOf("month"), "day")).toBe(true);
  });
});

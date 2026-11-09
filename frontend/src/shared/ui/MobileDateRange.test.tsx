import { fireEvent, render, screen } from "@testing-library/react";
import dayjs from "dayjs";
import { expect, it, vi } from "vitest";
import { MobileDateRange } from "./MobileDateRange";

it("передаёт выбранную дату и сохраняет вторую границу", () => {
  const onChange = vi.fn();
  render(
    <MobileDateRange value={[dayjs("2026-11-01"), dayjs("2026-11-03")]} onChange={onChange} />,
  );
  fireEvent.change(screen.getByLabelText("Дата от"), { target: { value: "2026-11-02" } });
  expect(onChange.mock.calls[0]![0].map((date: dayjs.Dayjs) => date.format("YYYY-MM-DD"))).toEqual([
    "2026-11-02",
    "2026-11-03",
  ]);
});

it("позволяет очистить диапазон", () => {
  const onChange = vi.fn();
  render(
    <MobileDateRange value={[dayjs("2026-11-01"), dayjs("2026-11-03")]} onChange={onChange} />,
  );
  fireEvent.change(screen.getByLabelText("Дата до"), { target: { value: "" } });
  expect(onChange).toHaveBeenCalledWith(null);
});
